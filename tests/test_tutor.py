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
    assert tutor._parse_json(text) == EXPLANATION


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
