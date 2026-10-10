"""
Feynman AI Tutor — Streamlit edition
Built with Python for the "Built with Python Hackathon" (CS4Everyone, 2026).

Implements the 4 steps of the Feynman Technique:
  1. Explain it simply   2. Teach it back   3. Find the gaps   4. Re-simplify

Works in two modes:
  - Demo mode (no setup): uses built-in sample content, so anyone can try the flow.
  - Live AI mode: calls the Google Gemini API (you paste a free key) for any topic.
"""

import datetime

import streamlit as st

from tutor import call_gemini, demo_explain, demo_grade, explain_prompt, grade_prompt

# --------------------------------------------------------------------------- #
# Page config
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="Feynman AI Tutor", page_icon="🧠", layout="centered")

ss = st.session_state
ss.setdefault("explain", None)
ss.setdefault("grade", None)
ss.setdefault("topic", "")

EXAMPLES = ["Neural networks", "Compound interest", "Why the sky is blue", "What is an API",
            "Blockchain", "The greenhouse effect", "Recursion", "Supply and demand"]


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
