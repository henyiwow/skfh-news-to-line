from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, SourceGroup
import os

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_SECRET"))

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if isinstance(event.source, SourceGroup):
        group_id = event.source.group_id
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"👋 群組 ID 是：{group_id}")
        )

if __name__ == "__main__":
    app.run()
