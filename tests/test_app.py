"""用 Streamlit 內建的 AppTest 跑整個 app.py（無瀏覽器、不連網），確認畫面流程。"""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

import tutor

APP = str(Path(__file__).resolve().parent.parent / "app.py")
LIVE = "⚡ Live AI (Gemini)"


def start_app():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception
    return at


def click(at, label):
    next(b for b in at.button if b.label == label).click().run()
    assert not at.exception


def teach(at, topic):
    next(t for t in at.text_input if t.label == "Topic").input(topic)
    click(at, "✨ Teach me")


def test_app_starts_in_demo_mode():
    at = start_app()

    assert at.title[0].value == "🧠 Feynman AI Tutor"
    assert at.sidebar.radio[0].value.startswith("🧪 Demo mode")


def test_demo_mode_runs_all_four_steps_without_a_key():
    at = start_app()
    teach(at, "Compound interest")

    assert "2 · Explain it simply" in [s.value for s in at.subheader]
    assert any(tutor.DEMO["Compound interest"]["simple"] in m.value for m in at.markdown)

    answer = "Interest is added to the balance, and then that interest earns interest too."
    at.text_area(key="user_text").input(answer)
    click(at, "🔍 Find my gaps")

    score = tutor.demo_grade("Compound interest", answer)["score"]
    assert "4 · Your understanding & gaps" in [s.value for s in at.subheader]
    assert at.metric[0].value == f"{score} / 100"


def test_live_mode_without_a_key_shows_an_error():
    at = start_app()
    at.sidebar.radio[0].set_value(LIVE).run()
    teach(at, "Recursion")

    assert at.error[0].value == "No Gemini key yet — paste one in the sidebar, or use Demo mode."
    assert "2 · Explain it simply" not in [s.value for s in at.subheader]


def test_live_mode_renders_the_gemini_reply(gemini):
    gemini.reply(json.dumps({
        "simple": "Recursion means a function calls itself.",
        "analogy": "Like standing between two mirrors.",
        "keypoints": ["Needs a base case"],
        "checkQuestions": ["What stops the recursion?"],
    }))
    at = start_app()
    at.sidebar.radio[0].set_value(LIVE).run()
    at.sidebar.text_input[0].input("test-key")
    teach(at, "Recursion")

    assert len(gemini.calls) == 1
    assert "/models/gemini-3.6-flash:" in gemini.calls[0]["url"]
    assert any("Recursion means a function calls itself." in m.value for m in at.markdown)
    assert at.success[0].value == "Like standing between two mirrors."


def live_app(gemini, reply):
    gemini.reply(reply)
    at = start_app()
    at.sidebar.radio[0].set_value(LIVE).run()
    at.sidebar.text_input[0].input("test-key")
    return at


def test_live_mode_shows_a_readable_error_for_a_garbled_reply(gemini):
    at = live_app(gemini, "Sorry, I can't help with that.")
    teach(at, "Recursion")

    assert at.error[0].value == "The AI reply wasn't in the expected format. Please try again."
    assert "2 · Explain it simply" not in [s.value for s in at.subheader]


def test_live_mode_renders_a_reply_with_missing_fields(gemini):
    # 回歸：舊版少了 analogy / keypoints 會直接 KeyError
    at = live_app(gemini, json.dumps({"simple": "Recursion means a function calls itself."}))
    teach(at, "Recursion")

    assert "2 · Explain it simply" in [s.value for s in at.subheader]


def test_live_grade_accepts_a_score_written_as_text(gemini):
    # 回歸：舊版 int("85/100") 會讓整頁噴錯
    at = live_app(gemini, json.dumps(tutor.DEMO["What is an API"]))
    teach(at, "What is an API")
    gemini.reply(json.dumps({"score": "85/100", "gaps": ["Mention the base case"]}))
    at.text_area(key="user_text").input("A function that calls itself.")
    click(at, "🔍 Find my gaps")

    assert at.metric[0].value == "85 / 100"
    assert any("Mention the base case" in m.value for m in at.markdown)


ENV_CAPTION = "Using GEMINI_API_KEY from the server environment."
REPLY = json.dumps(tutor.DEMO["Neural networks"])


def test_live_mode_falls_back_to_the_environment_key(gemini, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    gemini.reply(REPLY)
    at = start_app()
    at.sidebar.radio[0].set_value(LIVE).run()
    teach(at, "Neural networks")

    assert ENV_CAPTION in [c.value for c in at.sidebar.caption]
    assert gemini.calls[0]["headers"] == {"x-goog-api-key": "env-key"}
    assert at.sidebar.text_input[0].value == ""  # 金鑰不會回填到瀏覽器端的欄位


def test_a_typed_key_wins_over_the_environment_key(gemini, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    at = live_app(gemini, REPLY)
    teach(at, "Neural networks")

    assert ENV_CAPTION not in [c.value for c in at.sidebar.caption]
    assert gemini.calls[0]["headers"] == {"x-goog-api-key": "test-key"}
