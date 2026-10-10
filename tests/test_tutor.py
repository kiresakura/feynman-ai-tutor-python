import json

import pytest

import tutor

EXPLANATION = {
    "simple": "Recursion is when a function calls itself on a smaller piece of the problem.",
    "analogy": "Like Russian nesting dolls: open one and there is a smaller one inside.",
    "keypoints": ["It needs a base case", "Each call works on a smaller input"],
    "checkQuestions": ["What is a base case?"],
}


# --- Demo 模式 ------------------------------------------------------------- #
def test_demo_explain_returns_built_in_content_for_known_topic():
    assert tutor.demo_explain("Compound interest") == tutor.DEMO["Compound interest"]


def test_demo_explain_builds_generic_content_for_any_other_topic():
    result = tutor.demo_explain("Blockchain")

    assert set(result) == {"simple", "analogy", "keypoints", "checkQuestions"}
    assert "Blockchain" in result["simple"]
    assert all("Blockchain" in q for q in result["checkQuestions"])


@pytest.mark.parametrize(
    ("user_text", "score"),
    [("", 20), ("   ", 20), ("abcd", 46), ("x" * 40, 55), ("x" * 1000, 92)],
)
def test_demo_grade_scores_by_answer_length(user_text, score):
    assert tutor.demo_grade("Recursion", user_text)["score"] == score


def test_demo_grade_lists_nothing_correct_for_an_empty_answer():
    assert tutor.demo_grade("Recursion", "")["correct"] == []
    assert tutor.demo_grade("Recursion", "my answer")["correct"]


# --- Prompts ---------------------------------------------------------------- #
def test_explain_prompt_asks_for_the_json_fields_the_ui_reads():
    prompt = tutor.explain_prompt("Recursion", "middle school")

    assert '"Recursion"' in prompt
    assert "middle school" in prompt
    for field in ("simple", "analogy", "keypoints", "checkQuestions"):
        assert f'"{field}"' in prompt


def test_grade_prompt_includes_the_student_answer():
    prompt = tutor.grade_prompt("Recursion", "A function that calls itself.")

    assert '"""A function that calls itself."""' in prompt
    for field in ("score", "correct", "gaps", "resimple"):
        assert f'"{field}"' in prompt


# --- JSON 解析 -------------------------------------------------------------- #
@pytest.mark.parametrize(
    "text",
    [
        json.dumps(EXPLANATION),
        "```json\n" + json.dumps(EXPLANATION) + "\n```",
        "Sure! Here is the JSON you asked for:\n" + json.dumps(EXPLANATION) + "\nHope it helps.",
    ],
    ids=["plain", "fenced", "wrapped-in-text"],
)
def test_parse_json_recovers_the_object(text):
    assert tutor.parse_json(text) == EXPLANATION


# --- 呼叫 Gemini（假的 requests.post，不連網） ------------------------------ #
def test_call_gemini_posts_prompt_and_parses_reply(gemini):
    gemini.reply(json.dumps(EXPLANATION))

    result = tutor.call_gemini("PROMPT", "test-key", "gemini-test")

    assert result == EXPLANATION
    (call,) = gemini.calls
    assert ":generateContent" in call["url"]
    assert "/models/gemini-test:" in call["url"]
    assert call["json"]["contents"][0]["parts"][0]["text"] == "PROMPT"
    assert call["json"]["generationConfig"]["responseMimeType"] == "application/json"


def test_call_gemini_surfaces_the_api_error_message(gemini):
    gemini.status_code = 400
    gemini.payload = {"error": {"message": "API key not valid."}}

    with pytest.raises(RuntimeError, match=r"Gemini error \(400\)\. API key not valid\."):
        tutor.call_gemini("PROMPT", "bad-key", "gemini-test")


def test_call_gemini_falls_back_to_a_generic_hint_without_error_body(gemini):
    gemini.status_code = 429
    gemini.payload = ValueError("not JSON")

    with pytest.raises(RuntimeError, match="Check your key or quota"):
        tutor.call_gemini("PROMPT", "test-key", "gemini-test")


def test_parse_json_keeps_the_word_json_inside_an_untagged_fence():
    # 回歸：舊版會把第一個 "json" 字樣當成語言標記刪掉，內容被改壞
    data = {"simple": "A .json file stores data as text."}

    assert tutor.parse_json("```\n" + json.dumps(data) + "\n```") == data


def test_parse_json_ignores_braces_in_trailing_text():
    # 回歸：舊版從第一個 { 切到最後一個 }，後面多一段 {…} 就解析失敗
    text = json.dumps(EXPLANATION) + "\nNote: fields follow the {schema} you gave."

    assert tutor.parse_json(text) == EXPLANATION


@pytest.mark.parametrize(
    "text",
    ["", "Sorry, I can't help with that.", "null", "[1, 2, 3]", "{not json at all}"],
    ids=["empty", "prose", "null", "array", "broken-object"],
)
def test_parse_json_rejects_replies_without_a_json_object(text):
    with pytest.raises(tutor.AIResponseError, match="expected format"):
        tutor.parse_json(text)


@pytest.mark.parametrize(
    "payload",
    [{"promptFeedback": {"blockReason": "SAFETY"}}, {"candidates": []}, {"candidates": [{"finishReason": "SAFETY"}]}],
    ids=["prompt-blocked", "no-candidates", "no-content"],
)
def test_call_gemini_explains_a_reply_without_content(gemini, payload):
    gemini.payload = payload

    with pytest.raises(tutor.AIResponseError, match="no answer"):
        tutor.call_gemini("PROMPT", "test-key", "gemini-test")


# --- 欄位整理：缺欄位、型別錯、分數越界 ------------------------------------ #
def test_normalize_explanation_keeps_a_complete_reply():
    assert tutor.normalize_explanation(EXPLANATION) == EXPLANATION


def test_normalize_explanation_fills_missing_optional_fields():
    assert tutor.normalize_explanation({"simple": "  Short answer.  "}) == {
        "simple": "Short answer.",
        "analogy": "",
        "keypoints": [],
        "checkQuestions": [],
    }


@pytest.mark.parametrize("simple", [None, "", "   ", ["a", "list"], 42])
def test_normalize_explanation_rejects_a_reply_without_explanation(simple):
    with pytest.raises(tutor.AIResponseError, match="no explanation"):
        tutor.normalize_explanation({**EXPLANATION, "simple": simple})


def test_normalize_explanation_turns_odd_types_into_lists_of_text():
    result = tutor.normalize_explanation(
        {"simple": "S", "analogy": ["not", "text"], "keypoints": "Only one point",
         "checkQuestions": ["Q1", "", None, 3, {"q": "Q2"}, " Q3 "]}
    )

    assert result["analogy"] == ""
    assert result["keypoints"] == ["Only one point"]
    assert result["checkQuestions"] == ["Q1", "Q3"]


@pytest.mark.parametrize(
    ("raw", "score"),
    [
        (0, 0), (73, 73), (100, 100),
        (150, 100), (-5, 0), (10**400, 100),
        (85.9, 85), ("85", 85), (" 85 ", 85), ("85/100", 85), ("85%", 85), ("-20", 0),
        ("excellent", 0), (None, 0), ([90], 0), (float("nan"), 0), (float("inf"), 0),
    ],
)
def test_clamp_score_always_returns_an_int_from_0_to_100(raw, score):
    assert tutor.clamp_score(raw) == score


def test_normalize_grade_fills_defaults_for_missing_fields():
    assert tutor.normalize_grade({}) == {"score": 0, "correct": [], "gaps": [], "resimple": ""}


def test_normalize_grade_cleans_a_messy_reply():
    result = tutor.normalize_grade(
        {"score": "120", "correct": "Used an analogy", "gaps": ["Base case", "  "], "resimple": None}
    )

    assert result == {"score": 100, "correct": ["Used an analogy"], "gaps": ["Base case"], "resimple": ""}


@pytest.mark.parametrize(
    ("score", "start"),
    [(100, "Great"), (80, "Great"), (79, "Nice"), (55, "Nice"), (54, "Don't worry"), (0, "Don't worry")],
)
def test_score_label_thresholds(score, start):
    assert tutor.score_label(score).startswith(start)


# --- explain / grade：Demo 與 Live 的分流 ----------------------------------- #
LIVE = {"live": True, "api_key": "test-key", "model": "gemini-test"}
DEMO_MODE = {"live": False, "api_key": "", "model": "gemini-test"}


def test_demo_mode_needs_no_key_and_never_calls_gemini(gemini):
    assert tutor.explain("Recursion", "middle school", **DEMO_MODE) == tutor.demo_explain("Recursion")
    assert tutor.grade("Recursion", "It calls itself.", **DEMO_MODE) == tutor.demo_grade(
        "Recursion", "It calls itself."
    )
    assert gemini.calls == []


@pytest.mark.parametrize("api_key", ["", "   "])
def test_live_mode_requires_a_key_before_calling_gemini(gemini, api_key):
    with pytest.raises(ValueError, match="No Gemini key yet"):
        tutor.explain("Recursion", "middle school", **{**LIVE, "api_key": api_key})
    assert gemini.calls == []


def test_live_explain_returns_validated_fields(gemini):
    gemini.reply("Here you go: " + json.dumps({"simple": "S", "keypoints": "One point"}))

    result = tutor.explain("Recursion", "middle school", **LIVE)

    assert result == {"simple": "S", "analogy": "", "keypoints": ["One point"], "checkQuestions": []}
    assert "middle school" in gemini.calls[0]["json"]["contents"][0]["parts"][0]["text"]


def test_live_grade_clamps_the_score(gemini):
    gemini.reply(json.dumps({"score": 250, "gaps": ["Base case"]}))

    result = tutor.grade("Recursion", "It calls itself.", **LIVE)

    assert result["score"] == 100
    assert result["gaps"] == ["Base case"]
