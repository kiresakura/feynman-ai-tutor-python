# 🧠 Feynman AI Tutor（費曼 AI 家教）

[![CI](https://github.com/kiresakura/feynman-ai-tutor-python/actions/workflows/ci.yml/badge.svg)](https://github.com/kiresakura/feynman-ai-tutor-python/actions/workflows/ci.yml)
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://feynman-ai-tutor-python-khbzd29lttjj9kz2wzfqgz.streamlit.app/)

[English](README.md) | 繁體中文

**真正學會任何主題：先用白話解釋給你聽，再請你講回來，最後精準指出你還沒懂的地方。**
以 Python + Streamlit 打造的網頁應用，為 *Built with Python Hackathon*（CS4Everyone，2026）製作。

**線上試用：** <https://feynman-ai-tutor-python-khbzd29lttjj9kz2wzfqgz.streamlit.app/>
預設為 Demo 模式，不必註冊、不用貼 API 金鑰，就能走完整個流程。

## 費曼學習法四步驟

1. **用簡單的話解釋** — 選主題與程度，取得白話解釋、生活化比喻、重點整理與自我檢查問題。
2. **換你講一次** — 用自己的話把概念寫出來。
3. **找出盲點** — 取得 0–100 的理解分數、你講對的地方，以及漏掉的盲點。
4. **再簡化一次** — 針對盲點用更簡單的方式重講；整份內容可匯出成 Markdown 學習筆記。

## 兩種模式

| | Demo 模式（預設） | Live AI 模式 |
|---|---|---|
| 設定 | 不需要 | Google Gemini API 金鑰 |
| 主題 | 4 個內建主題，其他主題套用通用範本 | 任何主題 |
| 回饋 | 依回答長度估算的示範分數 | 由 Gemini 評分你的解釋 |
| 網路 | 不呼叫任何 API | 呼叫 Gemini REST API |

## 本機執行（約 5 分鐘）

需要 Python 3.11 以上（CI 在 3.11–3.14 測試）。

```bash
git clone https://github.com/kiresakura/feynman-ai-tutor-python.git
cd feynman-ai-tutor-python
python -m venv .venv
source .venv/bin/activate        # Windows：.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

開啟 <http://localhost:8501>。預設為 **Demo 模式**，不用金鑰就能走完四個步驟。

## Live AI 模式（選用）

1. 到 [Google AI Studio](https://aistudio.google.com/apikey) 免費申請 API 金鑰。
2. 在側邊欄選 **⚡ Live AI (Gemini)** 並貼上金鑰；或在 `.env` 檔設定一次：

   ```bash
   cp .env.example .env      # 再填入 GEMINI_API_KEY
   ```

可選模型：`gemini-3.6-flash`（預設）與 `gemini-3.1-flash-lite`。
貼上的金鑰只存在你的 Streamlit session，並放在請求標頭（request header）送給 Google，不會出現在網址裡。

### 環境變數

| 變數 | 必填 | 用途 |
|---|---|---|
| `GEMINI_API_KEY` | 否 | 側邊欄金鑰欄位空白時，Live AI 模式改用這把金鑰；側邊欄輸入的金鑰永遠優先。可來自環境變數、本機 `.env` 檔，或 Streamlit secrets 最上層的設定。 |

> ⚠️ 公開部署時若設定了 `GEMINI_API_KEY`，所有訪客的 Live AI 請求都會使用你的金鑰與額度。不設定時，訪客需自備金鑰。

## 運作方式

- **`app.py`** — Streamlit 介面：session 狀態、輸入元件、進度條與 Markdown 匯出。
- **`tutor.py`** — 不依賴 Streamlit 的純 Python 邏輯：
  - 費曼 prompts，以及用 `requests` 呼叫 Gemini REST API（要求 `application/json` 輸出）；
  - 防呆的 JSON 解析，能容忍程式碼圍欄與 JSON 前後的多餘文字；
  - 欄位驗證：補齊缺漏欄位、把分數限制在 0–100，並把格式錯誤或被擋下的回覆轉成看得懂的錯誤訊息；
  - Demo 模式的內容與評分。

## 測試與 CI

```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

共 76 個測試，完全離線：socket 連線一律封鎖，Gemini 以假的 `requests.post` 取代，不需要金鑰或網路。
涵蓋 JSON 解析（圍欄、夾雜文字、亂回）、缺漏或型別錯誤的欄位、越界分數、被擋下的回覆、Demo 路徑，以及透過 Streamlit `AppTest` 跑完整四步驟畫面。
GitHub Actions 會在每次 push 與 pull request 時，於 Python 3.11–3.14 執行 ruff 與 pytest。

## 專案結構

```text
app.py                Streamlit 介面
tutor.py              prompts、呼叫 Gemini、解析與驗證、Demo 內容
tests/                pytest 測試（離線）
requirements.txt      執行所需套件
requirements-dev.txt  執行所需套件＋pytest 與 ruff
.env.example          選用的 GEMINI_API_KEY
```

## 部署

Fork 這個 repo，即可在 [Streamlit Community Cloud](https://share.streamlit.io) 免費部署：用 GitHub 登入 → 選擇 repo → 主程式選 `app.py`。

## 授權

MIT
