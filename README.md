# 🧠 Feynman AI Tutor — Python / Streamlit

> Learn any topic for real, using Richard Feynman's technique. The AI explains it in plain words, asks **you** to teach it back, finds your blind spots, then re-explains them. **Built with Python + Streamlit** for the *Built with Python Hackathon* (CS4Everyone, 2026).

## What it does
A Streamlit web app that runs the 4 steps of the Feynman Technique:

1. **Explain it simply** — pick a topic and depth; the app returns a plain explanation + a real-life analogy + key points.
2. **Teach it back** — you explain it in your own words.
3. **Find the gaps** — the app scores your understanding (0–100) and lists what you got right vs. missed.
4. **Re-simplify** — it re-teaches only your gaps.

Plus: comprehension questions, one-click **export to a Markdown study note**, and a **Demo mode** that runs with zero setup.

## How Python was used
- **Streamlit** builds the entire UI and handles state (`st.session_state`), inputs, buttons, progress bar, and the download button — all in pure Python.
- **`requests`** calls the **Google Gemini** REST API and requests structured JSON (`responseMimeType: application/json`); a small Python parser (`_parse_json`) defensively recovers the JSON so the UI never breaks on a messy response.
- The **Feynman prompts** and the **Demo-mode content/grading logic** are plain Python functions, so the whole 4-step flow works even without an API key.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
Opens at `http://localhost:8501`. It starts in **Demo mode** — no key needed.

## Use real AI (any topic)
Get a free key at [Google AI Studio](https://aistudio.google.com/apikey), open the sidebar → **Live AI (Gemini)** → paste the key. The key stays in your Streamlit session and is only used to call Google directly.

## Deploy (optional)
Push this repo to GitHub and deploy free on **[Streamlit Community Cloud](https://share.streamlit.io)** (sign in with GitHub → pick the repo → `app.py`).

## Files
- `app.py` — the whole app
- `requirements.txt` — `streamlit`, `requests`
- `README.md` — this file

## License
MIT
