
from linebot.v3.messaging.models import TemplateMessage, CarouselTemplate, CarouselColumn, MessageAction

def Carousel_Template():
    carousel_template_message = TemplateMessage(
        alt_text='Carousel template',
        template=CarouselTemplate(
            columns=[
                CarouselColumn(
                    thumbnail_image_url='https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/Number_1_in_green_rounded_square.svg/200px-Number_1_in_green_rounded_square.svg.png',
                    title='股票相關功能',
                    text='基本面相關功能',
                    actions=[
                        MessageAction(label="歷史股價圖", text="股價圖"),
                        MessageAction(label="歷史股價資訊", text="股價資訊"),
                        MessageAction(label="歷史股價資訊", text="股價資訊")
                    ]
                ),
                CarouselColumn(
                    thumbnail_image_url='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRuo7n2_HNSFuT3T7Z9PUZmn1SDM6G6-iXfRC3FxdGTj7X1Wr0RzA',
                    title='其他相關功能',
                    text='預測功能',
                    actions=[
                        MessageAction(label="預測股價", text="預測股價"),
                        MessageAction(label="股價新聞", text="股價新聞"),
                        MessageAction(label="股價分析GPT", text="股價分析GPT")
                    ]
                )
            ]
        )
    )
    return carousel_template_message







