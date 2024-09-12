import pandas as pd
import datetime as dt # 時間套件
from datetime import datetime
from linebot.v3.messaging import TextMessage

# 指定CSV檔案的路徑
file_path = '2330.TW_summary.csv'

# 使用pandas讀取CSV檔案
df = pd.read_csv(file_path)

def get_stock_price(stock_code):

  df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d') # 假設日期格式是 YYYY-MM-DD
  today_date = date.today() # 獲取當前日期
  today_data = df[df['Date'] == today_date]

  # 根據股票代碼進行進一步篩選
  matching_row = today_data[today_data['公司 代號_x'] == stock_code]

  # 判斷是否找到匹配的資料
  if not matching_row.empty:
    send_text = ("月營收：",df.iloc[matching_row,15])
    send_text += ("月營業額費用：",df.iloc[matching_row,45])
    send_text += print("每股盈餘：",df.iloc[matching_row,49])
    message = TextMessage(text=send_text)
  else:
    send_text =("未找到相對應日期和股票代碼的資料。")
    message = TextMessage(text=send_text)
  return message