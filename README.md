# 🧠 Feynman AI Tutor

[![CI](https://github.com/kiresakura/feynman-ai-tutor-python/actions/workflows/ci.yml/badge.svg)](https://github.com/kiresakura/feynman-ai-tutor-python/actions/workflows/ci.yml)
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://feynman-ai-tutor-python-khbzd29lttjj9kz2wzfqgz.streamlit.app/)

English | [繁體中文](README.zh-TW.md)

**Learn any topic for real: the app explains it simply, has you teach it back, then shows exactly what you missed.**
A Python + Streamlit web app built for the *Built with Python Hackathon* (CS4Everyone, 2026).

**Live demo:** <https://feynman-ai-tutor-python-khbzd29lttjj9kz2wzfqgz.streamlit.app/>
It starts in Demo mode, so you can try the whole flow without signing up or pasting an API key.

## The Feynman Technique in four steps

1. **Explain it simply** — pick a topic and a level; get a plain-language explanation, a real-life analogy, key points and check questions.
2. **Teach it back** — write the idea in your own words.
3. **Find the gaps** — get a 0–100 understanding score, what you got right, and the blind spots you missed.
4. **Re-simplify** — the gaps are re-explained even more simply. Export everything as a Markdown study note.

## Two modes

| | Demo mode (default) | Live AI mode |
|---|---|---|
| Setup | None | A Google Gemini API key |
| Topics | 4 built-in explanations, plus a generic template for any other topic | Any topic |
| Feedback | A simple demo score based on answer length | Gemini grades your explanation |
| Network | Never calls an API | Calls the Gemini REST API |

## Run locally (about 5 minutes)

Requires Python 3.11 or newer (CI tests 3.11–3.14).

```bash
git clone https://github.com/kiresakura/feynman-ai-tutor-python.git
cd feynman-ai-tutor-python
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open <http://localhost:8501>. The app starts in **Demo mode** — all four steps work with no key.

## Live AI mode (optional)

1. Get a free API key at [Google AI Studio](https://aistudio.google.com/apikey).
2. In the sidebar choose **⚡ Live AI (Gemini)** and paste the key — or save it once in a `.env` file:

   ```bash
   cp .env.example .env      # then fill in GEMINI_API_KEY
   ```

Models offered: `gemini-3.6-flash` (default) and `gemini-3.1-flash-lite`.
A pasted key stays in your Streamlit session and is sent to Google in a request header, never in the URL.

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | No | Used by Live AI mode when the sidebar key field is empty; a key typed in the sidebar always wins. Read from the environment, a local `.env` file, or a root-level Streamlit secret. |

> ⚠️ If you deploy publicly with `GEMINI_API_KEY` set, every visitor's Live AI requests use your key and quota. Leave it unset to have visitors bring their own key.

## How it works

- **`app.py`** — the Streamlit UI: session state, inputs, progress bar and the Markdown export.
- **`tutor.py`** — plain-Python logic with no Streamlit import:
  - the Feynman prompts and the Gemini REST call via `requests`, asking for `application/json` output;
  - a defensive JSON parser that tolerates code fences and extra text around the JSON;
  - validation that fills missing fields, clamps the score to 0–100 and turns malformed or blocked replies into readable error messages;
  - the Demo-mode content and grading.

## Tests and CI

```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

76 tests, fully offline: sockets are blocked and Gemini is replaced by a fake `requests.post`, so no key or network is needed.
They cover the JSON parser (fenced, wrapped and garbage replies), missing or mistyped fields, out-of-range scores, blocked responses, the Demo path, and the full four-step UI driven through Streamlit's `AppTest`.
GitHub Actions runs ruff and pytest on Python 3.11–3.14 for every push and pull request.

## Project layout

```text
app.py                Streamlit UI
tutor.py              prompts, Gemini call, parsing and validation, demo content
tests/                pytest suite (offline)
requirements.txt      runtime dependencies
requirements-dev.txt  runtime dependencies + pytest and ruff
.env.example          optional GEMINI_API_KEY
```

## Deploy

Fork the repo and deploy it free on [Streamlit Community Cloud](https://share.streamlit.io): sign in with GitHub → pick the repo → main file `app.py`.

## License

MIT
