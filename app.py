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
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    StickerMessageContent,
    ImageMessageContent,
    AudioMessageContent,
    VideoMessageContent,
    LocationMessageContent,
    FileMessageContent,
)

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


def send_line_reply(reply_token: str, message_text: str):
    """封裝 LINE 訊息回覆邏輯"""
    if not configuration:
        return
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=message_text)],
                )
            )
    except Exception as err:
        app.logger.error(f"傳送 LINE 回覆訊息失敗: {err}")


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
        "你是一個聰明、熱心且幽默有禮的 LINE 個人智慧助理，名字叫做「智聊小精靈」。"
        "請一律使用繁體中文（台灣繁體習慣）回覆。"
        "【排版與長度重要規則】\n"
        "1. 回覆總長度嚴格控制在 250 至 450 字之間（最長絕對不可超過 500 字）。\n"
        "2. 務必在限制長度內把語意完整表達完畢，有頭有尾，切勿話說到一半斷掉！請以完整的句子句號結束。\n"
        "3. 請減少或不要使用 Markdown 的雙星號粗體標籤（例如 **文字**），LINE 訊息不需要過多的星號，請改用自然換行或清晰標點呈現。\n"
        "4. 適當使用親切的 emoji 與簡短的條列整理，適合手機 LINE 上快速瀏覽閱讀。"
    )

    models_to_try = [
        "gemini-flash-latest",
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-flash-lite-latest",
    ]

    for model_name in models_to_try:
        try:
            # 提高 max_output_tokens 確保中文字元充足，絕不因 token 不足而在半句中斷
            response = gemini_client.models.generate_content(
                model=model_name,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=2048,
                ),
            )
            if response and response.text:
                text = response.text.strip()
                # 去除 LINE 聊天室中多餘的 ** 星號
                text = text.replace("**", "")
                # 確保長度不超過 500 字，若超出則在最近的句點安全截斷
                if len(text) > 500:
                    truncated = text[:495]
                    last_punct = max(
                        truncated.rfind("。"),
                        truncated.rfind("！"),
                        truncated.rfind("？"),
                        truncated.rfind("\n"),
                    )
                    if last_punct > 250:
                        text = truncated[: last_punct + 1]
                    else:
                        text = truncated + "..."
                return text
        except Exception as e:
            app.logger.warning(f"嘗試模型 {model_name} 失敗: {e}，切換備用模型...")
            continue

    return "抱歉，AI 大腦目前暫時連線繁忙，請稍候再試一次！"


@app.route("/", methods=["GET"])
def index():
    return "智聊小精靈 (LINE Gemini AI Smart Bot) v1.0 改善版運作中！Webhook 端點為 /callback"


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "version": "1.0.1-improved",
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


# 註冊訊息處理器
if handler:

    # 1. 文字訊息處理器 (AI 智慧對話 + 輸入防呆引導 + 內建指令)
    @handler.add(MessageEvent, message=TextMessageContent)
    def handle_message(event):
        raw_text = event.message.text
        user_text = raw_text.strip() if raw_text else ""

        # 情境 A：空白或純空白輸入處理 (輸入不完整)
        if not user_text:
            reply = (
                "【智聊小精靈提示】\n"
                "您輸入的訊息好像是空白的喔！請輸入您想詢問的內容，例如：\n"
                "• 「推薦台北一日遊景點」\n"
                "• 「請幫我寫一封請假信草稿」\n"
                "💡 輸入「說明」可查看完整使用指南！"
            )
            send_line_reply(event.reply_token, reply)
            return

        # 情境 B：純表情符號 (emoji) 或 (emoji) 標籤，已讀不回
        if user_text == "(emoji)" or (
            hasattr(event.message, "emojis")
            and event.message.emojis
            and not user_text.replace("(emoji)", "").strip()
        ):
            try:
                print(f"收到來自使用者 [{event.source.user_id}] 的純 Emoji 表情符號，已讀不回覆。")
            except Exception:
                pass
            return

        # 情境 C：內建功能指令 (說明 / help)
        if user_text.lower() in ["說明", "功能", "指令", "help", "/help", "指南"]:
            guide = (
                "🤖【智聊小精靈 功能指南】\n\n"
                "我是您的專屬生活智慧助理，具備繁體中文生活問答與寫作能力！\n\n"
                "✨【推薦使用方式】\n"
                "1. 旅遊行程：輸入「推薦花蓮兩天一夜行程」\n"
                "2. 文案撰寫：輸入「幫我寫給主管的專案進度回報信」\n"
                "3. 知識解答：輸入「請用簡單比喻解釋量子電腦」\n"
                "4. 語言翻譯：輸入「請將這段話翻成流利日文」\n\n"
                "💡【貼心提示】\n"
                "• 輸入文字請盡量具體，回答會更精準喔！\n"
                "• 傳送貼圖會自動已讀不回，節省額度～\n"
                "• 目前僅支援文字，暫不支援語音/影片/檔案分析。"
            )
            send_line_reply(event.reply_token, guide)
            return

        # 情境 D：輸入不完整 / 模糊關鍵字引導提醒
        incomplete_dict = {
            "推薦": (
                "哈囉！收到您的「推薦」需求～請問您想要哪一種類型的推薦呢？😄\n\n"
                "1. 🍽️ 美食餐廳（請提供地點、預算或料理類型）\n"
                "2. 🏖️ 旅遊景點（請提供天數、縣市或旅行偏好）\n"
                "3. 🎬 電影書籍（請提供喜愛的題材類型）\n\n"
                "請補充詳細一點的線索，小精靈就能為您量身打造精準推薦喔！✨"
            ),
            "幫我": (
                "沒問題！小精靈隨時為您服務 🙋‍♂️\n\n"
                "請告訴我具體需要幫忙的事情，例如：\n"
                "• 「幫我寫一封求職感謝信」\n"
                "• 「幫我翻譯這段英文」\n"
                "• 「幫我規劃 3 天 2 夜行程」\n\n"
                "請直接把您的詳細需求告訴我即可！💡"
            ),
            "查詢": (
                "請問您想查詢什麼資訊呢？請告訴我關鍵字，例如「查詢台北今天天氣」或「查詢機器學習定義」！💡"
            ),
        }

        if user_text in incomplete_dict:
            send_line_reply(event.reply_token, incomplete_dict[user_text])
            return

        # 短字問候快速引導
        if user_text.lower() in ["你好", "您好", "嗨", "hi", "hello", "在嗎", "安安"]:
            greeting = (
                "嗨！我是「智聊小精靈」✨\n"
                "今天有什麼我可以協助您的嗎？您可以隨時向我詢問生活問題、旅遊規劃或文案靈感！\n\n"
                "💡 輸入「說明」可查看完整功能清單喔！"
            )
            send_line_reply(event.reply_token, greeting)
            return

        # 情境 E：正常問題輸入，呼叫 Gemini AI 取得回答
        try:
            print(f"收到來自使用者 [{event.source.user_id}] 的問題: {user_text}")
        except Exception:
            pass

        ai_reply = ask_gemini(user_text)

        try:
            print(f"Gemini AI 回覆: {ai_reply[:60]}...")
        except Exception:
            pass

        send_line_reply(event.reply_token, ai_reply)

    # 2. 貼圖訊息處理器 (收到貼圖已讀不回)
    @handler.add(MessageEvent, message=StickerMessageContent)
    def handle_sticker_message(event):
        try:
            print(
                f"收到來自使用者 [{event.source.user_id}] 的貼圖 (package: {event.message.package_id}, sticker: {event.message.sticker_id})，已讀不回覆。"
            )
        except Exception:
            pass
        return

    # 3. 不支援的訊息格式處理器：圖片訊息
    @handler.add(MessageEvent, message=ImageMessageContent)
    def handle_image_message(event):
        hint = (
            "【智聊小精靈使用提示】📷\n"
            "收到您的圖片囉！目前改善版主要專注於文字智慧問答與生活諮詢，尚未支援圖片視覺辨識分析功能。\n\n"
            "請直接以文字輸入您的問題與我互動～💡\n"
            "（輸入「說明」可查看支援的功能清單）"
        )
        send_line_reply(event.reply_token, hint)

    # 4. 不支援的訊息格式處理器：語音訊息
    @handler.add(MessageEvent, message=AudioMessageContent)
    def handle_audio_message(event):
        hint = (
            "【智聊小精靈使用提示】🎙️\n"
            "收到您的語音訊息！目前小精靈僅支援文字訊息交流，暫不支援語音辨識喔。\n\n"
            "請改用文字輸入告訴我您的問題，我會立刻為您解答！"
        )
        send_line_reply(event.reply_token, hint)

    # 5. 不支援的訊息格式處理器：影片訊息
    @handler.add(MessageEvent, message=VideoMessageContent)
    def handle_video_message(event):
        hint = (
            "【智聊小精靈使用提示】🎥\n"
            "收到您的影片！目前小精靈暫不支援影片解析功能，請直接輸入文字與我對話～"
        )
        send_line_reply(event.reply_token, hint)

    # 6. 不支援的訊息格式處理器：地理位置訊息
    @handler.add(MessageEvent, message=LocationMessageContent)
    def handle_location_message(event):
        hint = (
            "【智聊小精靈使用提示】📍\n"
            "收到位置資訊！目前小精靈暫不支援即時定位分析，請直接打字告訴我您想查詢的地點或附近景點（例如：「推薦台北信義區美食」）！"
        )
        send_line_reply(event.reply_token, hint)

    # 7. 不支援的訊息格式處理器：檔案訊息
    @handler.add(MessageEvent, message=FileMessageContent)
    def handle_file_message(event):
        hint = (
            "【智聊小精靈使用提示】📁\n"
            "收到檔案！目前小精靈暫不支援文件讀取，請直接複製檔案內的文字內容發送給我，我立刻幫您整理或分析！"
        )
        send_line_reply(event.reply_token, hint)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port, debug=True)
