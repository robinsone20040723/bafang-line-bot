import os

from dotenv import load_dotenv
from fastapi import APIRouter, Request, HTTPException

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from app.services.chatbot_service import handle_message


# 載入 .env
load_dotenv()

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")


# 檢查環境變數是否存在
if not LINE_CHANNEL_SECRET:
    raise RuntimeError("找不到 LINE_CHANNEL_SECRET，請檢查 .env")

if not LINE_CHANNEL_ACCESS_TOKEN:
    raise RuntimeError("找不到 LINE_CHANNEL_ACCESS_TOKEN，請檢查 .env")


# LINE Webhook Handler
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# LINE Messaging API 設定
configuration = Configuration(
    access_token=LINE_CHANNEL_ACCESS_TOKEN
)


router = APIRouter(
    prefix="/line",
    tags=["LINE"]
)


@router.post("/webhook")
async def line_webhook(request: Request):
    """
    LINE Messaging API Webhook 接收入口。

    流程：
    1. 接收 LINE Webhook
    2. 取得 X-Line-Signature
    3. 驗證 LINE 簽章
    4. 交給 WebhookHandler 處理事件
    """

    signature = request.headers.get("X-Line-Signature")

    if not signature:
        raise HTTPException(
            status_code=400,
            detail="缺少 X-Line-Signature"
        )

    body = await request.body()
    body = body.decode("utf-8")

    try:
        handler.handle(body, signature)

    except InvalidSignatureError:
        raise HTTPException(
            status_code=400,
            detail="LINE Signature 驗證失敗"
        )

    return {
        "status": "ok"
    }


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    """
    處理 LINE 使用者傳入的文字訊息。
    """

    # 取得使用者輸入文字
    user_message = event.message.text

    # 呼叫我們原本已完成的 Chatbot
    result = handle_message(user_message)

    # 取得 Chatbot 最終回覆文字
    reply_text = result.get(
        "message",
        "抱歉，我目前無法處理這個問題。"
    )

    # 呼叫 LINE Messaging API 回覆
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(
                        text=reply_text
                    )
                ]
            )
        )