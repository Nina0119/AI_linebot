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
import openai  # Import OpenAI
from message import *
from stock import *
import datetime as dt
import numpy as np
from bs4 import BeautifulSoup

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

def handle_regular_message(messaging_api, event, msg, user_id):
    if "股價圖" in msg:
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="請輸入歷史股價XXX")]  # Suggest the correct format for the stock price request
            )
        )

    elif '目錄' in msg:
        message = Carousel_Template()
        reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[message])
        messaging_api.reply_message(reply_message)
    if '股票分析' in msg:
        stock_id = msg.replace("股票分析", "").strip()
        reply_data = stock_gpt(stock_id)
        messaging_api.reply_message(reply_data)
    elif '股價資訊' in msg:
        stock_id = msg.replace("股價資訊", "").strip()
        stock_data = stock_price(stock_id)
        price_data = format_stock_data(stock_data)
        messaging_api.reply_message(price_data)
    elif '股票新聞' in msg:
        stock_id = msg.replace("股票新聞", "").strip()
        news_data = stock_news(stock_id)
        formatted_news = format_news_data(news_data)
        messaging_api.reply_message(formatted_news )
    elif '歷史股價' in msg:
        try:
            stock_code = msg.replace("歷史股價", "").strip() + ".TW"  # Assume TSE stock code by adding .TW

            if not stock_code.replace(".TW", "").isdigit():  # Validate stock code format
                raise ValueError("Invalid stock code format")

            # Fetch stock data
            stock = yf.Ticker(stock_code)
            hist = stock.history(period="1mo")  # Get stock data for the last month

            if hist.empty:
                raise ValueError("No stock data available")

            # Plot stock prices
            dates = hist.index
            prices = hist['Close']

            plt.figure(figsize=(10, 5))
            plt.plot(dates, prices, label='Close Price')
            plt.title(f'{stock_code} - Last 31 days stock prices')
            plt.xlabel('Date')
            plt.ylabel('Close Price')
            plt.legend()

            # Save plot to memory
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)

            # Upload image to Imgur
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

            # Reply with the image
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[image_message]
                )
            )

        except ValueError as ve:
            # Handle known errors like invalid stock code
            logging.error(f"Value Error: {str(ve)}")
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=str(ve))]
                )
            )
        except Exception as e:
            # Handle general errors
            logging.error(f"Error: {str(e)}")
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=f'Unable to retrieve stock data for {stock_code}. Please check the stock code.')]
                ))

    else:   # New command to interact with GPT
        try:
            prompt = f"User asked: {msg}\nYour response:"
            # Generate a response using OpenAI's API
            response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=256,
            temperature=0.5,
        )

            gpt_response = response["choices"][0]["message"]["content"].strip()

            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=gpt_response)]
                )
            )
        except openai.error.OpenAIError as e:
            if "quota" in str(e):
                error_message = "不好意思，ChatGPT額度用完了。請Key '目錄' 查看其他選項。"
            else:
                error_message = "Sorry, something went wrong with OpenAI API."

            logging.error(f"Error with OpenAI API: {str(e)}")
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=error_message)]
                )
            )


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
