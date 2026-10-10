# 🤖 LINE Bot — Gemini AI 智慧助理

一個基於 **Flask** + **LINE Messaging API v3** + **Google Gemini AI** 的 LINE 聊天機器人。
傳送任何文字訊息即可獲得 AI 智慧回覆，完全免費部署。

---

## ✨ 功能特色

| 功能 | 說明 |
|------|------|
| 🧠 Gemini AI 對話 | 接收使用者文字訊息，呼叫 Google Gemini API 回覆智慧答案 |
| 🔄 模型自動降級 | 依序嘗試多個 Gemini 模型，遇到 503 高流量時自動切換備用模型 |
| 📏 輸出長度控制 | 回覆嚴格控制在 500 字以內，並在句點安全截斷，不會話說到一半斷掉 |
| 🎨 排版優化 | 自動移除 Markdown 粗體星號 (`**`)，適合 LINE 聊天介面閱讀 |
| 😶 貼圖/Emoji 已讀不回 | 收到貼圖或純 Emoji 訊息時只記錄 log，不發送回覆 |
| 🛡️ 安全設計 | 所有金鑰存放於 `.env`（已 gitignore），不會洩漏至公開 repo |

---

## 📁 專案結構與文件交付 (Deliverables)

```
line-bot/
├── app.py                           # 主程式（Flask 伺服器 + LINE Webhook + Gemini AI）
├── requirements.txt                 # Python 套件依賴
├── .env.example                     # 環境變數範例（複製為 .env 並填入自己的金鑰）
├── .gitignore                       # Git 忽略規則（排除 .env 等機密檔案）
├── LINE_Bot_v1_Project_Plan.pdf    # 📄 專案計畫書正式文件 (A4 PDF)
├── LINE_Bot_v1_Presentation.pdf    # 📊 專案成果簡報投影片 (16:9 PDF)
├── LINE_Bot_v1_Project_Plan.html   # 專案計畫書網頁原始檔 (A4)
├── LINE_Bot_v1_Presentation.html   # 成果簡報投影片原始檔 (16:9)
└── LINE_Bot_v1_Executive_Summary.md # 執行摘要說明文件
```

---

## 🚀 快速開始

### 1. 複製專案

```bash
git clone https://github.com/41154B003Sam/line-bot.git
cd line-bot
```

### 2. 安裝依賴

```bash
pip install -r requirements.txt
```

### 3. 設定環境變數

```bash
cp .env.example .env
```

編輯 `.env`，填入你的金鑰：

```env
LINE_CHANNEL_SECRET=你的_LINE_Channel_Secret
LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_Channel_Access_Token
GEMINI_API_KEY=你的_Gemini_API_Key
PORT=5000
```

> 💡 **取得金鑰：**
> - LINE：前往 [LINE Developers Console](https://developers.line.biz/) 建立 Messaging API Channel
> - Gemini：前往 [Google AI Studio](https://aistudio.google.com/app/apikey) 免費取得 API Key

### 4. 啟動伺服器

```bash
python app.py
```

伺服器會在 `http://localhost:5000` 啟動。

### 5. 設定外部存取（二選一）

**方案 A：Cloudflare Tunnel（推薦，免費）**

```bash
# 安裝 cloudflared（Windows）
winget install cloudflare.cloudflared

# 啟動臨時通道
cloudflared tunnel --url http://localhost:5000
```

複製產生的 `https://xxx.trycloudflare.com` 網址。

**方案 B：ngrok**

```bash
ngrok http 5000
```

### 6. 設定 LINE Webhook

前往 LINE Developers Console → 你的 Channel → Messaging API：
- **Webhook URL** 設為 `https://你的外部網址/callback`
- 開啟 **Use webhook**
- 關閉 **Auto-reply messages**

---

## 🔧 API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/` | 伺服器狀態頁面 |
| GET | `/health` | 健康檢查（JSON 格式，顯示各金鑰是否已設定） |
| POST | `/callback` | LINE Webhook 接收端點 |

---

## ⚙️ 技術細節

- **LINE SDK**: `line-bot-sdk` v3（使用 `WebhookHandler` + `MessagingApi`）
- **AI 引擎**: Google Gemini（依序嘗試 `gemini-flash-latest` → `gemini-3.8-flash` → `gemini-3.5-flash` → `gemini-flash-lite-latest`）
- **System Prompt**: 控制回覆語言（繁體中文）、長度（250~450 字）、排版風格
- **Windows 相容**: 自動修正 `cp950` 編碼問題，確保 Emoji 不會造成程式崩潰

---

## 📝 License

此專案供學習與個人使用。
