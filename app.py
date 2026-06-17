"""
Feynman AI Tutor — Streamlit edition
Built with Python for the "Built with Python Hackathon" (CS4Everyone, 2026).

Implements the 4 steps of the Feynman Technique:
  1. Explain it simply   2. Teach it back   3. Find the gaps   4. Re-simplify

Works in two modes:
  - Demo mode (no setup): uses built-in sample content, so anyone can try the flow.
  - Live AI mode: calls the Google Gemini API (you paste a free key) for any topic.
"""

import json
import datetime
import requests
import streamlit as st

# --------------------------------------------------------------------------- #
# Page config
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="Feynman AI Tutor", page_icon="🧠", layout="centered")

ss = st.session_state
ss.setdefault("explain", None)
ss.setdefault("grade", None)
ss.setdefault("topic", "")

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

EXAMPLES = ["Neural networks", "Compound interest", "Why the sky is blue", "What is an API",
            "Blockchain", "The greenhouse effect", "Recursion", "Supply and demand"]


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
def _parse_json(text: str) -> dict:
    s = text.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1] if "```" in s[3:] else s
        s = s.replace("json", "", 1).strip().strip("`").strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        a, b = s.find("{"), s.rfind("}")
        if a >= 0 and b > a:
            return json.loads(s[a:b + 1])
        raise


def call_gemini(prompt: str, api_key: str, model: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.6, "responseMimeType": "application/json"},
    }
    r = requests.post(url, json=body, timeout=60)
    if r.status_code != 200:
        msg = ""
        try:
            msg = r.json().get("error", {}).get("message", "")
        except Exception:
            pass
        raise RuntimeError(f"Gemini error ({r.status_code}). {msg or 'Check your key or quota.'}")
    data = r.json()
    text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
    return _parse_json(text)


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
# Sidebar — engine settings
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("⚙️ Settings")
    mode = st.radio("Learning engine", ["🧪 Demo mode (no setup)", "⚡ Live AI (Gemini)"])
    live = mode.startswith("⚡")
    api_key, model = "", "gemini-2.0-flash"
    if live:
        api_key = st.text_input("Gemini API key", type="password",
                                help="Free key at https://aistudio.google.com/apikey")
        model = st.selectbox("Model", ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash"])
        st.caption("Your key is used only to call Google directly from this app. "
                   "Get a free one at [Google AI Studio](https://aistudio.google.com/apikey).")
    st.divider()
    st.caption("Built with Python · Streamlit · Google Gemini API")


def run_explain(topic: str, level: str) -> dict:
    if live:
        if not api_key.strip():
            st.error("No Gemini key yet — paste one in the sidebar, or use Demo mode.")
            return None
        return call_gemini(explain_prompt(topic, level), api_key.strip(), model)
    return demo_explain(topic)


def run_grade(topic: str, user_text: str) -> dict:
    if live:
        if not api_key.strip():
            st.error("No Gemini key yet — paste one in the sidebar, or use Demo mode.")
            return None
        return call_gemini(grade_prompt(topic, user_text), api_key.strip(), model)
    return demo_grade(topic, user_text)


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.title("🧠 Feynman AI Tutor")
st.caption("Learn anything for real — not just read about it")
st.info("**Mission:** Great tutors are expensive, but knowing *how to explain* shouldn't be a luxury. "
        "This tool uses Richard Feynman's technique to give anyone — on any topic — a patient tutor that "
        "teaches in plain words and analogies, then helps you catch what you don't actually understand yet.")

# --------------------------------------------------------------------------- #
# Step 1 — choose a topic
# --------------------------------------------------------------------------- #
st.subheader("1 · What do you want to learn?")
col1, col2 = st.columns([3, 2])
with col1:
    topic = st.text_input("Topic", value=ss.topic,
                          placeholder="e.g. neural networks, compound interest, blockchain…",
                          label_visibility="collapsed")
with col2:
    level = st.selectbox("Explain like I'm in…",
                         ["elementary school (simplest)", "middle school", "high school",
                          "university (technical ok)"], index=1)

st.write("Try an example:")
ex_cols = st.columns(4)
for i, ex in enumerate(EXAMPLES):
    if ex_cols[i % 4].button(ex, key=f"ex_{i}", use_container_width=True):
        topic = ex
        ss.topic = ex

if st.button("✨ Teach me", type="primary", use_container_width=True):
    if not topic.strip():
        st.warning("Type a topic first.")
    else:
        ss.topic = topic.strip()
        ss.grade = None
        with st.spinner(f"Breaking \"{ss.topic}\" down into the clearest form…"):
            try:
                ss.explain = run_explain(ss.topic, level)
            except Exception as e:  # noqa: BLE001
                ss.explain = None
                st.error(str(e))

# --------------------------------------------------------------------------- #
# Step 2 — explanation
# --------------------------------------------------------------------------- #
if ss.explain:
    d = ss.explain
    st.subheader("2 · Explain it simply")
    st.markdown(f"**💡 Simple explanation**\n\n{d['simple']}")
    st.markdown(f"**🔗 Real-life analogy**")
    st.success(d["analogy"])
    st.markdown("**📌 Key points**")
    for k in d["keypoints"]:
        st.markdown(f"- {k}")

    # Step 3 — teach it back
    st.subheader("3 · Now you explain it")
    st.caption("Teaching is the best way to learn. Say it in your own words; the AI shows what you haven't grasped.")
    with st.expander("🤔 Think about these first"):
        for i, q in enumerate(d.get("checkQuestions", []), 1):
            st.markdown(f"**Q{i}.** {q}")
    user_text = st.text_area("In your own words, explain this topic to someone who knows nothing about it:",
                             key="user_text", height=140)
    if st.button("🔍 Find my gaps", type="primary"):
        with st.spinner("Comparing your explanation and finding the gaps…"):
            try:
                ss.grade = run_grade(ss.topic, user_text)
            except Exception as e:  # noqa: BLE001
                ss.grade = None
                st.error(str(e))

# --------------------------------------------------------------------------- #
# Step 4 — gaps & score
# --------------------------------------------------------------------------- #
if ss.grade:
    g = ss.grade
    score = max(0, min(100, int(g.get("score", 0))))
    st.subheader("4 · Your understanding & gaps")
    st.progress(score / 100.0)
    label = ("Great — you really get it 🎉" if score >= 80
             else "Nice. Patch a couple of gaps and it's complete 💪" if score >= 55
             else "Don't worry — this is where progress starts 🌱")
    st.metric("Understanding", f"{score} / 100", label)
    if g.get("correct"):
        st.markdown("**✅ What you've got**")
        for c in g["correct"]:
            st.markdown(f"- {c}")
    if g.get("gaps"):
        st.markdown("**🎯 Gaps to close**")
        for c in g["gaps"]:
            st.markdown(f"- {c}")
    st.markdown("**🔁 Re-explained for your gaps**")
    st.success(g.get("resimple", ""))

    note = (f"# Feynman study note: {ss.topic}\n\n"
            f"Generated {datetime.datetime.now():%Y-%m-%d %H:%M}\n\n"
            f"## Simple explanation\n{ss.explain.get('simple','')}\n\n"
            f"## Real-life analogy\n{ss.explain.get('analogy','')}\n\n"
            f"## Key points\n" + "\n".join(f"- {k}" for k in ss.explain.get('keypoints', [])) + "\n\n"
            f"## Understanding\n{score} / 100\n\n"
            f"## Gaps to close\n" + "\n".join(f"- {k}" for k in g.get('gaps', [])) + "\n\n"
            f"## Gap fix\n{g.get('resimple','')}\n")
    st.download_button("📄 Export study notes", note,
                       file_name=f"feynman-note-{ss.topic.replace(' ', '-').lower()}.md")

st.divider()
st.caption("Feynman AI Tutor · built with Python + Streamlit for the Built with Python Hackathon · "
           "free, no tracking · your API key stays in your session.")
