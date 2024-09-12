from linebot.v3.messaging.models import ImageMessage, ButtonsTemplate, TemplateMessage, MessageAction
import requests
from bs4 import BeautifulSoup
import openai
import pandas as pd
import datetime as dt
import yfinance as yf
from linebot.v3.webhooks.models import MessageEvent
from linebot.v3.messaging.models import TextMessage
import numpy as np
import logging

def stock_price(stock_id, days=10):
    if stock_id == "大盤":
        stock_id = "^TWII"
    else:
        stock_id += ".TW"

    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    df = yf.download(stock_id, start=start)

    if df.empty:
        return TextMessage(text=f"無法取得 {stock_id} 的股價資訊。請確認股票代碼是否正確。")

    df.columns = ['開盤價', '最高價', '最低價', '收盤價', '調整後收盤價', '成交量']

    data_str = "\n".join([
        f"{date}: 收盤價={close:.2f}, 每日報酬={pct_chg:.4f}, 漲跌價差={diff:.2f}"
        for date, close, pct_chg, diff in zip(
            df.index.strftime('%Y-%m-%d').tolist(),
            df['收盤價'].tolist(),
            df['收盤價'].pct_change().tolist(),
            df['調整後收盤價'].diff().tolist()
        )
    ])

    message = TextMessage(text=data_str)
    return message



def get_stock_name(stock_id, name_df):
    return name_df.set_index('股號').loc[stock_id, '股名']


def stock_news(stock_id):
    if stock_id == "大盤":
        stock_name = "台股"
    else:
        stock_name = stock_id  # Use the stock_id directly as the stock_name if it's not "大盤"
    
    stock_name += " -盤中速報"  # Append the extra string to the stock name

    try:
        # Making the request to the news API
        response = requests.get(f'https://ess.api.cnyes.com/ess/api/v1/news/keyword?q={stock_name}&limit=5&page=1')
        response.raise_for_status()  # Ensure the request was successful
        
        # Parsing JSON data
        json_data = response.json()
        items = json_data.get('data', {}).get('items', [])
        
        if not items:
            return TextMessage(text=f"沒有找到 {stock_name} 的相關新聞。")

        news_list = []
        for item in items:
            title = item.get("title", "無標題")
            publish_at = item.get("publishAt", None)
            formatted_date = dt.datetime.utcfromtimestamp(publish_at).strftime('%Y-%m-%d') if publish_at else "無日期"
            news_url = f'https://news.cnyes.com/news/id/{item.get("newsId", "")}'
            
            news_list.append(f"{formatted_date}: {title}\n{news_url}\n")

        # Join all the news items into one message
        news_data_str = "\n".join(news_list)
        return TextMessage(text=news_data_str)

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching news: {str(e)}")
        return TextMessage(text=f"無法獲取 {stock_name} 的新聞資訊，請稍後再試。")

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return TextMessage(text="獲取新聞資訊時發生錯誤，請稍後再試。")


def format_stock_data(stock_data):
    formatted_data = "\n".join(
        f"{date}: 收盤價={close:.2f}, 每日報酬={pct_chg:.4f}, 漲跌價差={diff:.2f}"
        for date, close, pct_chg, diff in zip(stock_data['日期'], stock_data['收盤價'], stock_data['每日報酬'], stock_data['漲跌價差'])
    )
    message = TextMessage(text=formatted_data)
    return message


def generate_content_msg(stock_id, name_df):

    stock_name = get_stock_name(
        stock_id, name_df) if stock_id != "大盤" else stock_id

    # 獲取某支股票的價格資料
    price_data = stock_price(stock_id)
    # 獲取某支股票的相關新聞
    news_data = stock_news(stock_name)

    content_msg = '請依據以下資料來進行分析並給出一份完整的分析報告:\n'

    content_msg += f'近期價格資訊:\n {price_data}\n'

    # 對個股進行分析
    if stock_id != "大盤":
        stock_value_data = stock_fundamental(stock_id)
        content_msg += f'每季營收資訊：\n {stock_value_data}\n'

    content_msg += f'近期新聞資訊: \n {news_data}\n'
    content_msg += f'請給我{stock_name}近期的趨勢報告,請以詳細、嚴謹及專業的角度撰寫此報告,並提及重要的數字, reply in 繁體中文'

    return content_msg

# 使用 GPT 模型來生成針對特定股票的專業趨勢分析報告
def stock_gpt(stock_id, name_df):
    content_msg = generate_content_msg(stock_id, name_df)

    msg = [{
        # 用"system"角色設定GPT扮演的角色是專業證券分析師，並且需要基於給定的數據進行分析。
        "role": "system",
        "content": "你現在是一位專業的證券分析師, 你會統整近期的股價、基本面、新聞資訊等方面並進行分析, 然後生成一份專業的趨勢分析報告"
    }, {
        #包含了前面生成的 content_msg，即包含股票資料的訊息模板
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

    # Convert fundamental data to a string representation
    data_str = "\n".join(
        f"{date}: 營收成長率={revenue_growth:.2f}, EPS={eps:.2f}, EPS 季增率={eps_growth:.2f}"
        for date, revenue_growth, eps, eps_growth in zip(data['季日期'], data['營收成長率'], data['EPS'], data['EPS 季增率'])
    )

    return data_str
def stock_price2(stock_code):
    # 指定CSV檔案的路徑
    file_path = '2330.TW_summary.csv'

    # 使用pandas讀取CSV檔案
    df = pd.read_csv(file_path)

    # 確保日期格式正確
    df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
    
    # 獲取當前日期
    today_date = dt.today()

    # 找到今天的資料
    today_data = df[df['Date'] == today_date]

    # 根據股票代碼進行進一步篩選
    matching_row = today_data[today_data['公司 代號_x'] == stock_code]

    # 判斷是否找到匹配的資料
    if not matching_row.empty:
        # 從matching_row提取所需資料，注意這裡我們使用iloc和values來獲取數值
        month_revenue = matching_row.iloc[0, 15]
        monthly_expense = matching_row.iloc[0, 45]
        eps = matching_row.iloc[0, 49]

        # 格式化訊息
        send_text = f"月營收：{month_revenue}\n月營業額費用：{monthly_expense}\n每股盈餘：{eps}"
        message = TextMessage(text=send_text)
    else:
        send_text = "未找到相對應日期和股票代碼的資料。"
        message = TextMessage(text=send_text)

    return message


def get_reply(messages):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=messages
    )
    reply = response.choices[0].message.content
    return reply

