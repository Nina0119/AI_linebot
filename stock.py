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


def stock_price(stock_id="大盤", days = 10):
  #檢查stock_id是否等於"大盤"，若是則將其設置為 "^TWII"（台灣加權股價指數的代號）。否則將".TW"加到stock_id的末尾。
  if stock_id == "大盤":
    stock_id="^TWII"
  else:
    stock_id += ".TW"

  #設置資料的開始和結束時間。
  end = dt.date.today() # 資料結束時間，預設為當天的日期
  start = end - dt.timedelta(days=days) # 資料開始時間，從當天回溯 days 天的日期
  # 使用yfinance的download函數來獲取股票資料
  df = yf.download(stock_id, start=start)

  # 更換列名
  df.columns = ['開盤價', '最高價', '最低價',
                '收盤價', '調整後收盤價', '成交量']

  data = {
    '日期': df.index.strftime('%Y-%m-%d').tolist(),
    '收盤價': df['收盤價'].tolist(),
    '每日報酬': df['收盤價'].pct_change().tolist(),
    '漲跌價差': df['調整後收盤價'].diff().tolist()
    }

  return data
def stock_news(stock_name ="大盤"):
  if stock_name == "大盤":
    stock_name="台股"

  stock_name= stock_name + " -盤中速報"

  data=[]
  # 取得 Json 格式資料
  json_data = requests.get(f'https://ess.api.cnyes.com/ess/api/v1/news/keyword?q={stock_name}&limit=5&page=1').json()

  # 依照格式擷取資料
  items=json_data['data']['items']
  for item in items:
      # 網址、標題和日期
      news_id = item["newsId"]
      title = item["title"]
      publish_at = item["publishAt"]
      # 使用 UTC 時間格式
      utc_time = dt.datetime.utcfromtimestamp(publish_at)
      formatted_date = utc_time.strftime('%Y-%m-%d')
      # 前往網址擷取內容
      url = requests.get(f'https://news.cnyes.com/news/id/{news_id}').content
      soup = BeautifulSoup(url, 'html.parser')
      p_elements=soup .find_all('p')
      # 提取段落内容
      p=''
      for paragraph in p_elements[4:]:
          p+=paragraph.get_text()
      data.append([stock_name, formatted_date ,title,p])
  return data


def stock_price2(stock_code):
    # 指定CSV檔案的路徑
    file_path = '2330.TW_summary.csv'

    # 使用pandas讀取CSV檔案
    df = pd.read_csv(file_path)

    # 取得當前日期
    history_date = dt.datetime.today()

    # 確保日期格式正確
    df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')

    # 如果沒有提供歷史日期，則提示輸入日期
    if history_date is None:
        return TextMessage(text="請提供有效的歷史日期。")

    # 解析歷史日期，確保格式正確
    try:
        history_date = pd.to_datetime(history_date, format='%Y-%m-%d')
    except ValueError:
        return TextMessage(text="無效的日期格式，請使用 YYYY-MM-DD 格式。")

    # 找到歷史日期前三個月的日期
    previous_month_date = history_date - pd.DateOffset(months=3)

    # Print for debugging
    print("Previous month date:", previous_month_date)

    # 找到前三個月的資料
    previous_month_data = df[df['Date'] == previous_month_date]

    # 根據股票代碼進行進一步篩選
    matching_row = previous_month_data[previous_month_data['公司 代號_x'] == stock_code]

    # Print for debugging
    print("Matching row:", matching_row)

    # 判斷是否找到匹配的資料
    if not matching_row.empty:
        # 從matching_row提取所需資料
        month_revenue = matching_row.iloc[0, 15]
        monthly_expense = matching_row.iloc[0, 45]
        eps = matching_row.iloc[0, 49]

        # 格式化訊息
        send_text = f"月營收：{month_revenue}\n月營業額費用：{monthly_expense}\n每股盈餘：{eps}"
        message = TextMessage(text=send_text)
    else:
        send_text = "未找到前三個月對應日期和股票代碼的資料。"
        message = TextMessage(text=send_text)

    return message
