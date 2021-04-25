import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import datetime
import json

# Grafana資料擷取
user = 'tuser'
password = 'tuser'

ip = 'http://203.75.178.67:8080/api/datasources/proxy/1/'
name = 'iotdbfa'
measure = 'tank'
ad = 'vpi3600'
timestamp1 = '1619107200000ms'

def crawler(dbip, dbname, measurement, address, timestamp1):
    url = f"{dbip}query?db={dbname}&q=SELECT * FROM \"{measurement}\" WHERE \"device\"= \'{address}\' " \
          f"and time >= {timestamp1}"

    return url

# url_3800 = "http://203.75.178.67:8080/api/datasources/proxy/1/query?db=iotdbfa&q=SELECT * FROM \"tank\" WHERE (\"device\" = 'vpi3860') AND time >= 1619107200000ms"
url_3800 = crawler(ip, name, measure, ad, timestamp1)

r_3800 = requests.get(url=url_3800, params='iotdbfa' ,auth=(user, password))
js = r_3800.json()
print(r_3800)
# print(js["results"][0]["series"])
col = js["results"][0]["series"][0]["columns"]
df = pd.DataFrame(js["results"][0]["series"][0]["values"], columns=col)
print(df)
df.to_csv("test_36.csv")
"""
col = pd.DataFrame(js["results"][0]["series"][0]["columns"])
val = pd.DataFrame(js["results"][0]["series"][0]["values"])
print(col)
print(val)
"""

"""
def timestamp_datetime(value):
    format = '%Y-%m-%d %H:%M:%S'
# value為傳入的值為時間戳(整形)，如：1332888820
    t_value = time.localtime(value)
## 經過localtime轉換後變成
## time.struct_time(tm_year=2012, tm_mon=3, tm_mday=28, tm_hour=6, tm_min=53, tm_sec=40, tm_wday=2, tm_yday=88, tm_isdst=0)
# 最後再經過strftime函式轉換為正常日期格式。
    dt = time.strftime(format, t_value)
    return dt

for item in js["results"][0]["series"][0]["values"]:
    t = timestamp_datetime(item[0]/1000)
    print('時間: ', t, 'VPI3800-含浸爐真空度: ', item[1])
    time.sleep(5)

data_3600 = r_3600.txt
data_3800 = r_3800.txt
# 顯示各數值(含浸桶壓力值、真空度、溫度、電容值(ch1~ch6))

print("3600含浸桶真空度:", data_3600)
print("3800含浸桶真空度:", data_3800)
"""
# 製程階段判斷(->乾真空維持->注入樹脂->濕真空維持->加壓->加壓維持->第一次洩壓->完全洩壓/製程結束)
# 製程開始/抽真空

# 注入樹脂

# 濕真空維持

# 加壓

# 加壓維持

# 第一次洩壓

# 完全洩壓/製程結束
