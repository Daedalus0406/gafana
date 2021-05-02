import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
# import pandas_profiling
import numpy as np

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

columns_drop = ['DI', 'DO', 'data17', 'data18', 'data19', 'data2', 'data20', 'data21', 'data22', 'device', 'device_1', 'ice_twmp', 'liquid', 'resin_pressure', 'resin_temp', 'resin_vacuum', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6']
df = df.drop(columns_drop, axis=1)


df['time'] = df['time'].str.replace('T', ' ').str.replace('Z', '')

df['time'] = pd.to_datetime(df['time'], format="%Y-%m-%d %H:%M")

# print(df.time)

vac_bins = [0,3.3,700,900]
vac_labels = [0,1,2]
# vac_labels = ['low','P','high']
df['vac_status'] = pd.cut(x=df.infusion_vacuum, bins=vac_bins, labels=vac_labels)

pre_bins = [-np.inf,0.003,0.08,6.27,6.49,np.inf]
pre_labels = [0,1,2,3,4]
# pre_labels = ['buttom','dropping','rsing_start','drop_start', 'rsing_top']
df['pre_status'] = pd.cut(x=df.infusion_pressure, bins=pre_bins, labels=pre_labels)

df.to_csv("test_38.csv")

#數值折線圖

fig, ax1 = plt.subplots()
plt.title('Infusion Vacuum & Pressure')
plt.xlabel('time')

ax2 = ax1.twinx()

ax1.set_ylabel('Vacuum', color='tab:blue')
ax1.plot(df.time, df.infusion_vacuum, color='blue')
ax1.tick_params(axis='y', labelcolor='tab:blue')

ax2.set_ylabel('Pressure', color='green')
ax2.plot(df.time, df.infusion_pressure, color='green')
ax2.tick_params(axis='y', labelcolor='green')

fig.tight_layout()
plt.show()

#狀態折線圖
fig, ax3 = plt.subplots()
plt.title('Infusion Vacuum & Pressure')
plt.xlabel('time')

ax4 = ax3.twinx()

ax3.set_ylabel('vac_status', color='tab:blue')
ax3.plot(df.time, df.vac_status, color='blue')
ax3.tick_params(axis='y', labelcolor='tab:blue')

ax4.set_ylabel('pre_status', color='green')
ax4.plot(df.time, df.pre_status, color='green')
ax4.tick_params(axis='y', labelcolor='green')

fig.tight_layout()
plt.show()

# profile = pandas_profiling.ProfileReport(df)
# profile.to_file("output.html")

# print(len(df.index))

# 製程階段判斷(->乾真空維持->注入樹脂->濕真空維持->加壓->加壓維持->第一次洩壓->完全洩壓/製程結束)
# 製程開始/抽真空

cycle_col = ["vac_pump_time","vac_pump_idx", "vac_stable_time","vac_stable_idx", "pre_rise_time","pre_rise_idx", "pre_peak_time","pre_peak_idx",
             "pre_stable_time","pre_stable_idx", "pre_relief_time","pre_relief_idx", "pro_end_time","pro_end_idx", "running_time"]
cycle = pd.DataFrame(columns=cycle_col)
cycle_temp = [float("nan")] * len(cycle_col)
flag = 0
df_len = len(df.index)-1

for i, ds_temp in df.iterrows():
    if i+1 <= df_len :
        ds_temp_next = df.loc[i + 1, ["time", "vac_status", "pre_status"]]
        #print(ds_temp)

        if flag == 0 and ds_temp['vac_status'] == 2 and ds_temp_next['vac_status'] == 1:
            print("製程開始", ds_temp["time"])
            flag = 1
            cycle_temp[0], cycle_temp[1] = ds_temp["time"], i
        # 真空維持
        elif flag == 1 and ds_temp['vac_status'] == 0 and ds_temp_next['vac_status'] == 0:
            print("真空維持", ds_temp["time"])
            flag = 2
            cycle_temp[2], cycle_temp[3] = ds_temp["time"], i
        # 加壓開始
        elif flag == 2 and ds_temp['pre_status'] == 0 and ds_temp_next['pre_status'] > ds_temp['pre_status']:
            print("加壓開始", ds_temp["time"])
            flag = 3
            cycle_temp[4], cycle_temp[5] = ds_temp["time"], i
        # 加壓頂峰
        elif flag == 3 and ds_temp['vac_status'] == 2 and ds_temp['pre_status'] == 4:
            print("加壓頂峰", ds_temp["time"])
            flag = 4
            cycle_temp[6], cycle_temp[7] = ds_temp["time"], i
        # 加壓維持
        elif flag == 4 and ds_temp['pre_status'] == 3:
            print("加壓維持", ds_temp["time"])
            flag = 5
            cycle_temp[8], cycle_temp[9] = ds_temp["time"], i
        # 第一次洩壓
        elif flag == 5 and ds_temp['pre_status'] == 3 and ds_temp_next['pre_status'] == 2:
            print("洩壓", ds_temp["time"])
            flag = 6
            cycle_temp[10], cycle_temp[11] = ds_temp["time"], i
        # 完全洩壓/製程結束
        elif flag == 6 and ds_temp['pre_status'] == 1 and ds_temp_next['pre_status'] == 0:
            print("製程結束", ds_temp["time"])
            flag = 7
            cycle_temp[12], cycle_temp[13] = ds_temp["time"], i
            cycle_temp[14] = (pd.to_datetime(cycle_temp[12])-pd.to_datetime(cycle_temp[0])).total_seconds()/60

            print("稼動工時 : %d 分鐘" % cycle_temp[14])
            print("="*10)
        if flag == 7:
            cycle = cycle.append(pd.Series(cycle_temp, index=cycle_col), ignore_index=True)
            flag = 0
    else:
        break
cycle.to_csv("cycle_38.csv")

print(" %s 至 %s " % (df.time[0], df.time[df_len]))

df_len = len(df.index)-1
total_time = ((pd.to_datetime(df.time[df_len])-pd.to_datetime(df.time[0])).total_seconds()/60)
print("總開機時間 : %d 分鐘" % total_time)

total_run_time = total_time - cycle.loc[:,"running_time"].sum()
print("總稼動工時 : %d 分鐘" % total_run_time)

total_standby_time = total_time - total_run_time
print("總待機時間 : %d 分鐘" % total_standby_time)


