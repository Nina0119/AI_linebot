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

def stock_price2(stock_code):
    # 指定CSV檔案的路徑
    file_path = '2330.TW_summary.csv'

    # 使用pandas讀取CSV檔案
    df = pd.read_csv(file_path)

    # 確保日期格式正確
    df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')

    today_date = dt.date.today()

    # Print for debugging
    print("Today's date:", today_date)

    # 找到今天的資料
    today_data = df[df['Date'] == today_date]

    # Print for debugging
    print("Today's data from CSV:", today_data)

    # 根據股票代碼進行進一步篩選
    matching_row = today_data[today_data['公司 代號_x'] == stock_code]

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
        send_text = "未找到相對應日期和股票代碼的資料。"
        message = TextMessage(text=send_text)

    return message
