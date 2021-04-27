import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas_profiling

# Grafana資料擷取
user = 'tuser'
password = 'tuser'

ip = 'http://203.75.178.67:8080/api/datasources/proxy/1/'
name = 'iotdbfa'
measure = 'tank'
ad = 'vpi3860'
time1 = '1619193600000ms'
time2 = '1619279999999ms'

def crawler(dbip, dbname, measurement, address, timestamp1, timestamp2):
    url = f"{dbip}query?db={dbname}&q=SELECT * FROM \"{measurement}\" WHERE \"device\"= \'{address}\' " \
          f"and time >= {timestamp1}  "

    return url

# url_3800 = http://203.75.178.67:8080/api/datasources/proxy/1/query?db=iotdbfa&q=SELECT last("infusion_vacuum") FROM "tank" WHERE ("device" = 'vpi3860') AND time >= 1619280000000ms GROUP BY time(1m)"
url_3800 = crawler(ip, name, measure, ad, time1, time2)

r_3800 = requests.get(url=url_3800, params='iotdbfa' ,auth=(user, password))
js = r_3800.json()
print(r_3800)
# print(js["results"][0]["series"])
col = js["results"][0]["series"][0]["columns"]
df = pd.DataFrame(js["results"][0]["series"][0]["values"], columns=col)

columns_drop = ['DI', 'DO', 'data17', 'data18', 'data19', 'data2', 'data20', 'data21', 'data22', 'device', 'device_1', 'ice_twmp', 'liquid', 'resin_pressure', 'resin_temp', 'resin_vacuum']
df = df.drop(columns_drop, axis=1)


df['time'] = df['time'].str.replace('T', ' ').str.replace('Z', '')

df['time'] = pd.to_datetime(df['time'], format="%Y-%m-%d %H:%M")

# df['time'] = df['time'].apply(lambda _: datetime.strptime(_,"%Y-%m-%d %H:%M"))

# print(df.time)

fig, ax1 = plt.subplots()
plt.title('Infusion Vacuum & Pressure')
plt.xlabel('time')

ax2 = ax1.twinx()

ax1.set_ylabel('Vacuum', color='tab:blue')
ax1.plot(df.time, df.infusion_vacuum, color='tab:blue')
ax1.tick_params(axis='y', labelcolor='tab:blue')

ax2.set_ylabel('Pressure', color='black')
ax2.plot(df.time, df.infusion_pressure, color='black')
ax2.tick_params(axis='y', labelcolor='black')

fig.tight_layout()
plt.show()

# profile = pandas_profiling.ProfileReport(df)
# profile.to_file("output.html")

df.to_csv("test_38.csv")

