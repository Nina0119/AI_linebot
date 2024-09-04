from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks.models import MessageEvent, TextMessageContent
from linebot.v3.messaging.models import ImageMessage, ButtonsTemplate, TemplateMessage, MessageAction
import yfinance as yf
import matplotlib.pyplot as plt
import io
import os
from dotenv import load_dotenv
import logging
import requests
from message import *
from stock import *
import datetime as dt
import numpy as np
from bs4 import BeautifulSoup
import openai 

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Get environment variables
channel_access_token = os.getenv('channel_access_token')
channel_secret = os.getenv('channel_secret')
imgur_client_id = os.getenv('IMGUR_CLIENT_ID')
openai.api_key = os.getenv('openai_api_key')
if not openai.api_key:
    logging.error("OpenAI API key is not set.")  # Set OpenAI API key

# Configure Line Bot API and handler
configuration = Configuration(access_token=channel_access_token)
api_client = ApiClient(configuration)
messaging_api = MessagingApi(api_client)
handler = WebhookHandler(channel_secret)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Define callback route
@app.route("/")
def home():
    return "Webhook Running!!!"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    msg = event.message.text.strip()
    logging.info(f"Received message: {msg} from user: {user_id} with reply token: {event.reply_token}")

    # Route the message to the appropriate handler based on the content
    handle_regular_message(messaging_api, event, msg, user_id)

def handle_regular_message(messaging_api, event, msg, user_id):
    logging.info(f"Handling message: {msg}")

    if "股價圖" in msg:
        reply_text = "請輸入歷史股價XXX"
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

    elif '目錄' in msg:
        carousel = Carousel_Template()
        reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[carousel])
        messaging_api.reply_message(reply_message)

    elif '哪一隻' in msg:
        carousel = stock_buttons_template2()
        reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[carousel])
        messaging_api.reply_message(reply_message)
    elif '基本面' in msg:
        carousel = stock_buttons_template()
        reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[carousel])
        messaging_api.reply_message(reply_message)

    elif '股票分析GPT' in msg:
        stock_id = msg.replace("股票分析GPT", "").strip()
        reply_data = stock_gpt(stock_id)
        reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[reply_data])
        messaging_api.reply_message(reply_message)

    elif "股票news" in msg:
        reply_text = "請輸入股票新聞XXX"
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )
    elif "歷史股價資訊" in msg:
        reply_text = "請輸入股價資訊XXX"
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
            )
    elif '股價資訊' in msg:
        stock_id = msg.replace("股價資訊", "").strip()
        stock_data_message = stock_price(stock_id)
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[stock_data_message]
            )
        )
        logging.info("Replied with stock price information")


    elif '股票新聞' in msg:
        stock_id = msg.replace("股票新聞", "").strip()
        news_data = stock_news(stock_id)
        reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[news_data])
        messaging_api.reply_message(reply_message)

    elif '歷史股價' in msg:
        try:
            stock_code = msg.replace("歷史股價", "").strip() + ".TW"

            if not stock_code.replace(".TW", "").isdigit():
                raise ValueError("Invalid stock code format")

            stock = yf.Ticker(stock_code)
            hist = stock.history(period="1mo")

            if hist.empty:
                raise ValueError("No stock data available")

            dates = hist.index
            prices = hist['Close']

            plt.figure(figsize=(10, 5))
            plt.plot(dates, prices, label='Close Price')
            plt.title(f'{stock_code} - Last 31 days stock prices')
            plt.xlabel('Date')
            plt.ylabel('Close Price')
            plt.legend()

            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)

            headers = {'Authorization': f'Client-ID {imgur_client_id}'}
            files = {'image': buf.getvalue()}
            response = requests.post('https://api.imgur.com/3/image', headers=headers, files=files)

            if response.status_code == 200:
                image_url = response.json()['data']['link']
            else:
                raise Exception("Failed to upload image to Imgur")

            image_message = ImageMessage(
                original_content_url=image_url,
                preview_image_url=image_url
            )

            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[image_message]
                )
            )

        except ValueError as ve:
            logging.error(f"Value Error: {str(ve)}")
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=str(ve))]
                )
            )
        except Exception as e:
            logging.error(f"Error: {str(e)}")
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=f'Unable to retrieve stock data for {stock_code}. Please check the stock code.')]
                )
            )

    else:
        message = TextMessage(text='請輸入"目錄"查找功能')
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[message]
            )
        )
        logging.info("Replied with default message")




if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
