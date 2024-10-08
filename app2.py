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
from csv import *
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
