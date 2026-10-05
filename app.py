import io
import os
import sys
from dotenv import load_dotenv
from flask import Flask, request, abort, jsonify

# Windows 終端機 UTF-8 編碼修正，避免輸出 emoji 時引發 cp950 編碼崩潰
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from google import genai
from google.genai import types

# 載入 .env 環境變數
load_dotenv(override=True)

channel_secret = os.getenv("LINE_CHANNEL_SECRET")
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")
port = int(os.getenv("PORT", 5000))

app = Flask(__name__)

# LINE 設定
handler = WebhookHandler(channel_secret) if channel_secret else None
configuration = (
    Configuration(access_token=channel_access_token)
    if channel_access_token
    else None
)

# Gemini AI 客戶端
gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None


def ask_gemini(user_message: str) -> str:
    """呼叫 Google Gemini API 取得智慧回答"""
    global gemini_client
    current_key = os.getenv("GEMINI_API_KEY")
    if not gemini_client and current_key:
        gemini_client = genai.Client(api_key=current_key)

    if not gemini_client or not current_key:
        return (
            "【AI 智慧助理提示】\n"
            "尚未設定 GEMINI_API_KEY！\n"
            "請在專案的 .env 檔案中填入免費的 Gemini API Key，我就可以為您回答任何問題囉！"
        )

    system_prompt = (
        "你是一個聰明、熱心且幽默有禮的 LINE 個人智慧助理。"
        "請一律使用繁體中文（台灣繁體習慣）回覆。"
        "【排版與長度規則】\n"
        "1. 回覆總長度絕對嚴格控制在 500 字以內，精簡扼要，避免冗長廢話。\n"
        "2. 請減少或不要使用 Markdown 的雙星號粗體標籤（例如 **文字**），LINE 訊息不需要過多的星號，請改用自然換行或清晰標點呈現。\n"
        "3. 適當使用親切的 emoji 與簡短的條列整理，適合手機 LINE 上快速瀏覽閱讀。"
    )

    models_to_try = [
        "gemini-flash-latest",
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-flash-lite-latest",
    ]

    for model_name in models_to_try:
        try:
            response = gemini_client.models.generate_content(
                model=model_name,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=600,
                ),
            )
            if response and response.text:
                text = response.text.strip()
                # 去除 LINE 聊天室中多餘的 ** 星號
                text = text.replace("**", "")
                # 確保長度嚴格不超過 500 字
                if len(text) > 500:
                    text = text[:497] + "..."
                return text
        except Exception as e:
            app.logger.warning(f"嘗試模型 {model_name} 失敗: {e}，切換備用模型...")
            continue

    return "抱歉，AI 大腦目前暫時連線繁忙，請稍候再試一次！"


@app.route("/", methods=["GET"])
def index():
    return "LINE Gemini AI Smart Bot 運作中！請將 Webhook 指向 /callback"


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "has_line_secret": bool(channel_secret),
            "has_line_token": bool(channel_access_token),
            "has_gemini_key": bool(os.getenv("GEMINI_API_KEY")),
        }
    )


@app.route("/callback", methods=["POST"])
def callback():
    if not handler or not configuration:
        return "伺服器尚未設定 LINE 金鑰", 500

    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.warning("無效的簽章，拒絕請求。")
        abort(400)
    except Exception as e:
        app.logger.error(f"處理事件時發生錯誤: {e}")
        return "Internal Error", 500

    return "OK"


# 註冊文字訊息處理器 (AI 智慧對話)
if handler:

    @handler.add(MessageEvent, message=TextMessageContent)
    def handle_message(event):
        user_text = event.message.text.strip()
        try:
            print(f"收到來自使用者 [{event.source.user_id}] 的問題: {user_text}")
        except Exception:
            pass

        # 呼叫 Gemini AI 取得回答
        ai_reply = ask_gemini(user_text)

        try:
            print(f"Gemini AI 回覆: {ai_reply[:60]}...")
        except Exception:
            pass

        try:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=ai_reply)],
                    )
                )
        except Exception as err:
            app.logger.error(f"傳送 LINE 回覆訊息失敗: {err}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port, debug=True)
