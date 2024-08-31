
from linebot.v3.messaging.models import ImageMessage, ButtonsTemplate, TemplateMessage, MessageAction

def buttons_message():
    buttons_template = ButtonsTemplate(
        title="選單",
        text="請選擇一個選項",
        actions=[
            MessageAction(label="歷史股價圖", text="股價圖"),
            MessageAction(label="歷史股價資訊", text="股價資訊"),
            MessageAction(label="預測股價", text="預測股價"),
            MessageAction(label="股價新聞", text="股價新聞"),
            MessageAction(label="股價分析GPT", text="股價分析GPT"),
        ]
    )
    return TemplateMessage(alt_text="這是選單", template=buttons_template)

