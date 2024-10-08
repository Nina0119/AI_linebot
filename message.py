
from linebot.v3.messaging.models import TemplateMessage, CarouselTemplate, CarouselColumn, MessageAction, ButtonsTemplate

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
                        MessageAction(label="基本面資訊", text="基本面"),
                        MessageAction(label="歷史股價資訊", text="歷史股價資訊")
                    ]
                ),
                CarouselColumn(
                    thumbnail_image_url='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRuo7n2_HNSFuT3T7Z9PUZmn1SDM6G6-iXfRC3FxdGTj7X1Wr0RzA',
                    title='其他相關功能',
                    text='預測功能',
                    actions=[
                        MessageAction(label="股票新聞", text="股票news"),
                        MessageAction(label="預測股價", text="哪一隻"),
                        MessageAction(label="股價分析GPT", text="股價分析GPT")
                    ]
                )
            ]
        )
    )

    return carousel_template_message

def stock_buttons_template():
    buttons_template = TemplateMessage(
        alt_text='股票選單',
        template=ButtonsTemplate(
            title='股票選擇',
            text='請選擇以下股票',
            actions=[
                MessageAction(
                    label='台積電',
                    text='2330'
                ),
                MessageAction(
                    label='鴻海',
                    text='2317'
                )
            ]
        )
    )
    return buttons_template

def stock_buttons_template2():
    buttons_template = TemplateMessage(
        alt_text='股票選單',
        template=ButtonsTemplate(
            title='股票選擇',
            text='請選擇以下股票',
            actions=[
                MessageAction(
                    label='台積電預測',
                    text='台積電預測'
                ),
                MessageAction(
                    label='鴻海預測',
                    text='鴻海預測'
                )
            ]
        )
    )
    return buttons_template







