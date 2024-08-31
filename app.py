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

def stock_price(stock_id="大盤", days=10):
    if stock_id == "大盤":
        stock_id = "^TWII"
    else:
        stock_id += ".TW"

    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    df = yf.download(stock_id, start=start)

    df.columns = ['開盤價', '最高價', '最低價', '收盤價', '調整後收盤價', '成交量']

    data = {
        '日期': df.index.strftime('%Y-%m-%d').tolist(),
        '收盤價': df['收盤價'].tolist(),
        '每日報酬': df['收盤價'].pct_change().tolist(),
        '漲跌價差': df['調整後收盤價'].diff().tolist()
    }

    message = TextMessage(text=data)
    return message

def format_stock_data(stock_data):
    formatted_data = "\n".join(
        f"{date}: 收盤價={close:.2f}, 每日報酬={pct_chg:.4f}, 漲跌價差={diff:.2f}"
        for date, close, pct_chg, diff in zip(stock_data['日期'], stock_data['收盤價'], stock_data['每日報酬'], stock_data['漲跌價差'])
    )
    message = TextMessage(text=formatted_data)
    return message
    

def stock_name():
    response = requests.get('https://isin.twse.com.tw/isin/C_public.jsp?strMode=2')
    url_data = BeautifulSoup(response.text, 'html.parser')
    stock_company = url_data.find_all('tr')

    data = [
        (row.find_all('td')[0].text.split('\u3000')[0].strip(),
         row.find_all('td')[0].text.split('\u3000')[1],
         row.find_all('td')[4].text.strip())
        for row in stock_company[2:] if len(row.find_all('td')[0].text.split('\u3000')[0].strip()) == 4
    ]

    df = pd.DataFrame(data, columns=['股號', '股名', '產業別'])
    message = TextMessage(text=df)
    return message

name_df = stock_name()

def get_stock_name(stock_id, name_df):
    message = TextMessage(text=name_df.set_index('股號').loc[stock_id, '股名'])
    return message
    

def stock_news(stock_name="大盤"):
    if stock_name == "大盤":
        stock_name = "台股"

    stock_name = stock_name + " -盤中速報"

    data = []
    json_data = requests.get(f'https://ess.api.cnyes.com/ess/api/v1/news/keyword?q={stock_name}&limit=5&page=1').json()

    items = json_data['data']['items']
    for item in items:
        news_id = item["newsId"]
        title = item["title"]
        publish_at = item["publishAt"]
        utc_time = dt.datetime.utcfromtimestamp(publish_at)
        formatted_date = utc_time.strftime('%Y-%m-%d')

        url = requests.get(f'https://news.cnyes.com/news/id/{news_id}').content
        soup = BeautifulSoup(url, 'html.parser')
        p_elements = soup.find_all('p')
        p = ''.join([paragraph.get_text() for paragraph in p_elements[4:]])

        data.append([stock_name, formatted_date, title, p])
    

def format_news_data(news_data):
    formatted_data = "\n".join(
        f"{date}: {title}\n{content}"
        for _, date, title, content in news_data
    )
    message = TextMessage(text=formatted_data)
    return message

def generate_content_msg(stock_id, name_df):
    stock_name = get_stock_name(stock_id, name_df) if stock_id != "大盤" else stock_id
    price_data = stock_price(stock_id)
    news_data = stock_news(stock_name)

    content_msg = '請依據以下資料來進行分析並給出一份完整的分析報告:\n'
    content_msg += f'近期價格資訊:\n {format_stock_data(price_data)}\n'

    if stock_id != "大盤":
        stock_value_data = stock_fundamental(stock_id)
        content_msg += f'每季營收資訊：\n {stock_value_data}\n'
        content_msg += f'近期新聞資訊: \n {format_news_data(news_data)}\n'
        content_msg += f'請給我{stock_name}近期的趨勢報告,請以詳細、嚴謹及專業的角度撰寫此報告,並提及重要的數字, reply in 繁體中文'

    message = TextMessage(text=content_msg)
    return message

def stock_gpt(stock_id, name_df=name_df):
    content_msg = generate_content_msg(stock_id, name_df)

    msg = [{
        "role": "system",
        "content": "你現在是一位專業的證券分析師, 你會統整近期的股價、基本面、新聞資訊等方面並進行分析, 然後生成一份專業的趨勢分析報告"
    }, {
        "role": "user",
        "content": content_msg
    }]

    reply_data = get_reply(msg)
    message = TextMessage(text=reply_data)
    return message

def stock_fundamental(stock_id="大盤"):
    if stock_id == "大盤":
        return None

    stock_id += ".TW"
    stock = yf.Ticker(stock_id)

    quarterly_revenue_growth = np.round(stock.quarterly_financials.loc["Total Revenue"].pct_change(-1).dropna().tolist(), 2)
    quarterly_eps = np.round(stock.quarterly_financials.loc["Basic EPS"].dropna().tolist(), 2)
    quarterly_eps_growth = np.round(stock.quarterly_financials.loc["Basic EPS"].pct_change(-1).dropna().tolist(), 2)

    dates = [date.strftime('%Y-%m-%d') for date in stock.quarterly_financials.columns]

    data = {
        '季日期': dates[:len(quarterly_revenue_growth)],
        '營收成長率': quarterly_revenue_growth.tolist(),
        'EPS': quarterly_eps.tolist(),
        'EPS 季增率': quarterly_eps_growth.tolist()
    }

    message = TextMessage(text=data)
    return message

def get_reply(messages):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=messages
    )
    reply = response.choices[0].message.content
    return reply

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    msg = event.message.text.strip()
    logging.info(f"Received message: {msg} from user: {user_id} with reply token: {event.reply_token}")

    handle_regular_message(messaging_api, event, msg, user_id, name_df)


def handle_message(event):
    user_id = event.source.user_id
    msg = event.message.text.strip()
    logging.info(f"Received message: {msg} from user: {user_id} with reply token: {event.reply_token}")

    handle_regular_message(messaging_api, event, msg, user_id)

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
        messaging_api.reply_message(
            event.reply_token,
            TextMessage(text=reply_data)
        )
    elif '股價資訊' in msg:
        stock_id = msg.replace("股價資訊", "").strip()
        stock_data = stock_price(stock_id)
        price_data = format_stock_data(stock_data)
        messaging_api.reply_message(
            event.reply_token,
            TextMessage(text=price_data)
        )
    elif '股票新聞' in msg:
        stock_id = msg.replace("股票新聞", "").strip()
        news_data = stock_news(stock_id)
        formatted_news = format_news_data(news_data)
        messaging_api.reply_message(
            event.reply_token,
            TextMessage(text=formatted_news)
        )
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

if __name__ == "__main__":
    app.run(port=5000)
