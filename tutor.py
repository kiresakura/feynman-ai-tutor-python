"""
費曼家教的核心邏輯（不依賴 Streamlit，可單獨做單元測試）。

Demo 模式的內建內容與評分、Feynman prompts、呼叫 Gemini 並解析 JSON 回覆，
再把回覆整理成畫面固定使用的欄位（解釋、分數與盲點）。
"""

import json
import re

import requests

NO_KEY_MESSAGE = "No Gemini key yet — paste one in the sidebar, or use Demo mode."


class AIResponseError(ValueError):
    """模型回覆無法轉成畫面需要的資料；訊息會直接顯示給使用者。"""

# --------------------------------------------------------------------------- #
# Demo content (used when no API key / Demo mode)
# --------------------------------------------------------------------------- #
DEMO = {
    "Neural networks": {
        "simple": ("A neural network is a program loosely inspired by the brain. It's made of many "
                   "tiny 'units' wired together; each takes in numbers, does a simple calculation, and "
                   "passes the result on. By looking at lots of examples it tunes the strength of those "
                   "connections until it can recognize cats, understand speech, or predict the weather."),
        "analogy": ("Imagine a huge crowd playing telephone: the front row notices small details of a "
                    "picture and passes clues backward, until the last row shouts 'it's a cat!'. When "
                    "they're wrong, everyone adjusts what to pay attention to, so next time they're more accurate."),
        "keypoints": ["Made of 'layers' and 'nodes'; data flows forward layer by layer",
                      "Each connection has a 'weight' — how important that clue is",
                      "It 'trains' on lots of data, automatically adjusting the weights",
                      "Many layers = 'deep' learning"],
        "checkQuestions": ["What does a 'weight' do in a neural network?",
                           "Why does it need a lot of data to get accurate?",
                           "What does the 'deep' in deep learning refer to?"],
    },
    "Compound interest": {
        "simple": ("Compound interest means your interest earns interest too. Money you save grows by "
                   "some interest; you keep that interest, and next time it grows together with your "
                   "original amount. Over time the snowball rolls faster and faster."),
        "analogy": ("Like rolling a snowball downhill: it starts small, but each roll picks up new snow, "
                    "and the snow it picked up picks up even more snow next time."),
        "keypoints": ["Interest is reinvested to earn more interest",
                      "The longer the time, the more dramatic the effect",
                      "Higher rate and more frequent compounding grow it faster",
                      "Starting earlier makes a huge difference"],
        "checkQuestions": ["How is compound interest different from simple interest?",
                           "Why is time so important for compounding?",
                           "What happens if you start investing later?"],
    },
    "Why the sky is blue": {
        "simple": ("Sunlight looks white but is a mix of all colors. As it passes through the air, tiny "
                   "molecules scatter the light, and blue light — because it has a short wavelength — gets "
                   "scattered the most, spreading all over the sky."),
        "analogy": ("Like throwing balls of different sizes into a field of pegs: small balls (blue light) "
                    "bounce around and scatter everywhere; big balls (red light) mostly pass straight through."),
        "keypoints": ["White light contains all colors",
                      "Air molecules scatter light (Rayleigh scattering)",
                      "Blue has a short wavelength, so it scatters most",
                      "Sunsets are red because light travels farther and blue is scattered away"],
        "checkQuestions": ["Sunlight is white, so where does the blue come from?",
                           "What is 'scattering'?",
                           "Why is a sunset orange-red instead of blue?"],
    },
    "What is an API": {
        "simple": ("An API is a 'window' for one program to talk to another. You don't need to know how "
                   "the other side works inside — you just make a request in the agreed way and get a result. "
                   "Like a menu plus a waiter: you order, the kitchen cooks, the food comes out."),
        "analogy": ("An API is like a waiter: you tell the waiter 'I'd like meal A', the waiter takes it to "
                    "the kitchen (another program), and brings back the finished dish. You never enter the kitchen."),
        "keypoints": ["An agreed interface for programs to communicate",
                      "You deal only with the request and response, not internals",
                      "It lets different software connect and reuse features",
                      "Often it's a network request: send a question, get an answer"],
        "checkQuestions": ["Why can an API let you not know how the inside works?",
                           "In the restaurant analogy, what is the kitchen?",
                           "What's the benefit of an API for a developer?"],
    },
}


def demo_explain(topic: str) -> dict:
    if topic in DEMO:
        return DEMO[topic]
    return {
        "simple": (f"(Demo example) About \"{topic}\": first nail the one-sentence core — what it is and "
                   f"what problem it solves — then hang the details on that. Switch to Live AI mode in the "
                   f"sidebar to get a custom, in-depth explanation of \"{topic}\"."),
        "analogy": (f"Think of \"{topic}\" as an everyday situation you already know well, then find where "
                    f"the two work the same way — that makes the idea intuitive."),
        "keypoints": ["State in one sentence what it is",
                      "What problem it solves / why it matters",
                      "What steps its mechanism breaks into",
                      "A common misconception or exception"],
        "checkQuestions": [f"In one sentence, what is \"{topic}\"?",
                           f"What problem does \"{topic}\" solve?",
                           f"Can you give an example of \"{topic}\"?"],
    }


def demo_grade(topic: str, user_text: str) -> dict:
    n = len(user_text.strip())
    score = 20 if n == 0 else min(92, 45 + n // 4)
    return {
        "score": score,
        "correct": (["You explained it in your own words — the single most important Feynman step!",
                     "You captured some of the right direction."] if n > 0 else []),
        "gaps": ["(Demo feedback) Add one everyday analogy, and the 'why' behind how it works.",
                 "Check whether you used a technical term without explaining it clearly."],
        "resimple": (f"Quick reminder: when explaining \"{topic}\", first say what it is and what problem it "
                     f"solves, then finish with an analogy. Switch to Live AI mode for a precise analysis of "
                     f"your exact answer."),
    }


# --------------------------------------------------------------------------- #
# Gemini (REST) — no SDK needed, just requests
# --------------------------------------------------------------------------- #
def parse_json(text: str) -> dict:
    """取出回覆裡第一個完整的 JSON 物件；容忍 ```json 圍欄與前後的說明文字。"""
    decoder = json.JSONDecoder()
    start = text.find("{")
    while start != -1:
        try:
            return decoder.raw_decode(text, start)[0]
        except json.JSONDecodeError:
            start = text.find("{", start + 1)
    raise AIResponseError("The AI reply wasn't in the expected format. Please try again.")


def call_gemini(prompt: str, api_key: str, model: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.6, "responseMimeType": "application/json"},
    }
    r = requests.post(url, json=body, headers={"x-goog-api-key": api_key}, timeout=60)
    if r.status_code != 200:
        msg = ""
        try:
            msg = r.json().get("error", {}).get("message", "")
        except (ValueError, AttributeError):
            pass  # 錯誤內容不是預期的 JSON 物件，就用通用提示
        raise RuntimeError(f"Gemini error ({r.status_code}). {msg or 'Check your key or quota.'}")
    data = r.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        # 被安全機制擋下時，回覆裡沒有 candidates 或 content
        raise AIResponseError("Gemini returned no answer (it may have been blocked). "
                              "Try rephrasing.") from None
    text = "".join(p.get("text", "") for p in parts)
    return parse_json(text)


def explain_prompt(topic: str, level: str) -> str:
    return (
        f"You are a tutor who is a master of the Feynman Technique. You are warm and use plain language. "
        f"Explain the topic \"{topic}\" at the level of {level}. Respond with JSON ONLY (English), shape:\n"
        '{"simple":"3-5 plain sentences, no jargon dumping",'
        '"analogy":"one everyday real-life analogy",'
        '"keypoints":["3-4 must-know points, one sentence each"],'
        '"checkQuestions":["3 questions that test understanding, easy to hard"]}'
    )


def grade_prompt(topic: str, user_text: str) -> str:
    return (
        f"You are a Feynman-Technique tutor. A student tried to explain \"{topic}\" in their own words:\n"
        f'"""{user_text}"""\n'
        f"Assess their understanding. Be encouraging but honestly flag blind spots. JSON ONLY (English):\n"
        '{"score": integer 0-100,'
        '"correct":["what they got right, 0-3 items"],'
        '"gaps":["key blind spots they missed, 1-3 items"],'
        '"resimple":"re-explain the gaps even more simply, 2-4 sentences"}'
    )


# --------------------------------------------------------------------------- #
# 把模型回覆整理成畫面固定使用的欄位
# --------------------------------------------------------------------------- #
def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _items(value) -> list:
    """轉成字串清單：單一字串當成一項，非字串與空白項目略過。"""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def clamp_score(value) -> int:
    """轉成 0–100 的整數；"85/100"、"85%" 這類字串取開頭的數字，認不出來就是 0。"""
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value)
        value = float(match.group()) if match else 0
    try:
        score = int(value)
    except (TypeError, ValueError, OverflowError):
        score = 0
    return max(0, min(100, score))


def normalize_explanation(data: dict) -> dict:
    """補齊步驟 2 要顯示的欄位；連核心的 simple 都沒有，就當作這次回覆失敗。"""
    simple = _text(data.get("simple"))
    if not simple:
        raise AIResponseError("The AI reply had no explanation. Please try again.")
    return {
        "simple": simple,
        "analogy": _text(data.get("analogy")),
        "keypoints": _items(data.get("keypoints")),
        "checkQuestions": _items(data.get("checkQuestions")),
    }


def normalize_grade(data: dict) -> dict:
    """步驟 4 的分數與盲點；缺的欄位給空值，分數缺漏時為 0（與原本畫面的預設相同）。"""
    return {
        "score": clamp_score(data.get("score", 0)),
        "correct": _items(data.get("correct")),
        "gaps": _items(data.get("gaps")),
        "resimple": _text(data.get("resimple")),
    }


def score_label(score: int) -> str:
    if score >= 80:
        return "Great — you really get it 🎉"
    if score >= 55:
        return "Nice. Patch a couple of gaps and it's complete 💪"
    return "Don't worry — this is where progress starts 🌱"


def _require_key(api_key: str) -> str:
    key = api_key.strip()
    if not key:
        raise ValueError(NO_KEY_MESSAGE)
    return key


def explain(topic: str, level: str, *, live: bool, api_key: str, model: str) -> dict:
    """步驟 2：Demo 模式回內建內容；Live 模式問 Gemini 並驗證欄位。"""
    if not live:
        return demo_explain(topic)
    reply = call_gemini(explain_prompt(topic, level), _require_key(api_key), model)
    return normalize_explanation(reply)


def grade(topic: str, user_text: str, *, live: bool, api_key: str, model: str) -> dict:
    """步驟 4：Demo 模式依長度估分；Live 模式問 Gemini 並驗證欄位。"""
    if not live:
        return demo_grade(topic, user_text)
    reply = call_gemini(grade_prompt(topic, user_text), _require_key(api_key), model)
    return normalize_grade(reply)
