
from linebot.v3.messaging.models import ImageMessage, ButtonsTemplate, TemplateMessage, MessageAction
import requests
from bs4 import BeautifulSoup
import openai
import pandas as pd 
import datetime as dt
import yfinance as yf
from linebot.v3.webhooks.models import MessageEvent
from linebot.v3.messaging.models import TextMessage

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
    return name_df.set_index('股號').loc[stock_id, '股名']

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
    return data

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
    return reply_data

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

    return data

def get_reply(messages):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=messages
    )
    reply = response.choices[0].message.content
    return reply