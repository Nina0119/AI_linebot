
from linebot.v3.messaging.models import ImageMessage, ButtonsTemplate, TemplateMessage, MessageAction
import requests
from bs4 import BeautifulSoup
import openai
import pandas as pd 
import datetime as dt

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

def get_reply(messages):
  
        response = openai.ChatCompletion.create(
            model = "gpt-3.5-turbo-1106",
            # model = "gpt-4",
            messages = messages
        )
        reply = response.choices[0].message.content
   

# 創建一個給GPT模型的訊息模板（Prompt），用於生成特定股票的分析報告。
def stock_name():
  print("線上讀取股號、股名、及產業別")

  # 從台灣證券交易所的網站獲取股票清單
  response = requests.get('https://isin.twse.com.tw/isin/C_public.jsp?strMode=2')
  # 使用 BeautifulSoup 解析獲取的網頁內容
  url_data = BeautifulSoup(response.text, 'html.parser')
  # 從解析後的網頁中找到所有的 <tr> 標籤（表格行）。
  stock_company = url_data.find_all('tr')

  # 它檢查每一行第一個出現的<td>標籤，並將其分割為股號和股名。同時獲取了每一行的第五個<td>標籤中的產業別。
  data = [
      (row.find_all('td')[0].text.split('\u3000')[0].strip(),
        row.find_all('td')[0].text.split('\u3000')[1],
        row.find_all('td')[4].text.strip())
      for row in stock_company[2:] if len(row.find_all('td')[0].text.split('\u3000')[0].strip()) == 4
  ]

  # 使用提取的數據創建一個DataFrame，列名分別為'股號'、'股名'和'產業別'
  df = pd.DataFrame(data, columns=['股號', '股名', '產業別'])

  return df

name_df = stock_name()
def get_stock_name(stock_id, name_df):
    return name_df.set_index('股號').loc[stock_id, '股名']

print(name_df.head())
print("--------------------------")
print(get_stock_name("2330",name_df))
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

print(stock_news("台積電"))
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
def stock_gpt(stock_id, name_df=name_df):
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
def stock_fundamental(stock_id= "大盤"):
    if stock_id == "大盤":
        return None

    stock_id += ".TW"
    stock = yf.Ticker(stock_id)

    # 營收成長率
    quarterly_revenue_growth = np.round(stock.quarterly_financials.loc["Total Revenue"].pct_change(-1).dropna().tolist(), 2)

    # 每季EPS
    quarterly_eps = np.round(stock.quarterly_financials.loc["Basic EPS"].dropna().tolist(), 2)

    # EPS季增率
    quarterly_eps_growth = np.round(stock.quarterly_financials.loc["Basic EPS"].pct_change(-1).dropna().tolist(), 2)

    # 轉換日期
    dates = [date.strftime('%Y-%m-%d') for date in stock.quarterly_financials.columns]

    data = {
        '季日期': dates[:len(quarterly_revenue_growth)],
        '營收成長率': quarterly_revenue_growth.tolist(),
        'EPS': quarterly_eps.tolist(),
        'EPS 季增率': quarterly_eps_growth.tolist()
    }

    return data


