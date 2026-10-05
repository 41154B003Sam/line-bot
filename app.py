import os
import sys
from dotenv import load_dotenv
from flask import Flask, request, abort, jsonify

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

# 載入 .env 環境變數
load_dotenv()

channel_secret = os.getenv("LINE_CHANNEL_SECRET")
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
port = int(os.getenv("PORT", 5000))

app = Flask(__name__)

# 檢查金鑰是否存在
if not channel_secret or not channel_access_token:
    print(
        "【警告】尚未設定 LINE_CHANNEL_SECRET 或 LINE_CHANNEL_ACCESS_TOKEN！\n"
        "請在專案根目錄下的 .env 檔案中填入您的金鑰。",
        file=sys.stderr,
    )

handler = WebhookHandler(channel_secret) if channel_secret else None
configuration = (
    Configuration(access_token=channel_access_token)
    if channel_access_token
    else None
)


@app.route("/", methods=["GET"])
def index():
    return "LINE Echo Bot 伺服器運作中！請將 Webhook 指向 /callback"


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "has_secret": bool(channel_secret),
            "has_token": bool(channel_access_token),
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


# 註冊文字訊息處理器 (Echo 功能)
if handler:

    @handler.add(MessageEvent, message=TextMessageContent)
    def handle_message(event):
        user_text = event.message.text
        print(f"收到來自使用者 [{event.source.user_id}] 的訊息: {user_text}")

        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            # Echo: 原封不動回傳使用者輸入的內容
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=user_text)],
                )
            )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port, debug=True)
