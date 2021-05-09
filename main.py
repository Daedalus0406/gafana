"""
from bs4 import BeautifulSoup
import json
import matplotlib.dates as mdates
import pandas_profiling
"""
import time
import requests
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import datetime
import xlsxwriter
import smtplib
from email.mime.multipart import MIMEMultipart #email內容載體
from email.mime.text import MIMEText #用於製作文字內文
from email.mime.base import MIMEBase #用於承載附檔
from email import encoders #用於附檔編碼

# print (datetime.datetime.now())
# 回推報表起終點時間, 預設每周一早上八點觸發, 因應時區加八小時
# report_start_date = (datetime.datetime.now()+datetime.timedelta(days=-7)).strftime("%Y-%m-%d %H:%M:%S")
report_start_date = '2021-04-19 08:00:00'
start = datetime.datetime.strptime(report_start_date, '%Y-%m-%d %H:%M:%S')
# report_end_date = (datetime.datetime.now()+datetime.timedelta()).strftime("%Y-%m-%d %H:%M:%S")
report_end_date = '2021-04-26 08:00:00'


# print(report_start_date)
# print(report_end_date)


def datetime_timestamp(dt):
    time.strptime(dt, '%Y-%m-%d %H:%M:%S')
    s = time.mktime(time.strptime(dt, '%Y-%m-%d %H:%M:%S'))
    return int(s)


start_date_stamp = datetime_timestamp(report_start_date)
end_date_stamp = datetime_timestamp(report_end_date)

# Grafana資料擷取
user = 'tuser'
password = 'tuser'

ip = 'http://203.75.178.67:8080/api/datasources/proxy/1/'
name = 'iotdbfa'
measure = 'tank'
ad = 'vpi3860'

time1 = str(start_date_stamp) + 's'  # 2021-04-19 00:00:00
time2 = str(end_date_stamp) + 's'  # 2021-04-26 00:00:00


def crawler(dbip, dbname, measurement, address, timestamp1, timestamp2):
    url = f"{dbip}query?db={dbname}&q=SELECT * FROM \"{measurement}\" WHERE \"device\"= \'{address}\' " \
          f"and time >= {timestamp1} and time <= {timestamp2}"

    return url


url_3800 = crawler(ip, name, measure, ad, time1, time2)

r_3800 = requests.get(url=url_3800, params='iotdbfa', auth=(user, password))
js = r_3800.json()

if r_3800.status_code == 200:
    print('Grafana連線成功')
    print("=" * 20)

col = js["results"][0]["series"][0]["columns"]
df = pd.DataFrame(js["results"][0]["series"][0]["values"], columns=col)

columns_drop = ['DI', 'DO', 'data17', 'data18', 'data19', 'data2', 'data20', 'data21', 'data22', 'device', 'device_1',
                'ice_twmp', 'liquid', 'resin_pressure', 'resin_temp', 'resin_vacuum', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5',
                'ch6']
df = df.drop(columns_drop, axis=1)
# 整理時間欄位
df['time'] = df['time'].str.replace('T', ' ').str.replace('Z', '')
df['time'] = pd.to_datetime(df['time'], format="%Y-%m-%d %H:%M")

# 設置真空壓力狀態值
vac_bins = [0, 3.5, 700, 900]
vac_labels = [0, 1, 2]
# vac_labels = ['low','P','high']
df['vac_status'] = pd.cut(x=df.infusion_vacuum, bins=vac_bins, labels=vac_labels)

pre_bins = [-np.inf, 0.003, 0.08, 6.2, np.inf]
pre_labels = [0, 1, 2, 3]
# pre_labels = ['buttom','dropping','rsing_start','drop_start']
df['pre_status'] = pd.cut(x=df.infusion_pressure, bins=pre_bins, labels=pre_labels)

df.to_csv("test_38.csv")


# 產出自動化特徵分析
# profile = pandas_profiling.ProfileReport(df)
# profile.to_file("output.html")

# 製程階段判斷
# 製程開始/抽真空
def status_analyzer(filtered_df, start_date):
    cycle_col = ["vac_pump_time", "vac_pump_idx", "vac_stable_time", "vac_stable_idx", "pre_rise_time", "pre_rise_idx",
                 "pre_stable_time", "pre_stable_idx", "pre_relief_time", "pre_relief_idx", "pro_end_time",
                 "pro_end_idx",
                 "running_time"]
    cycle = pd.DataFrame(columns=cycle_col)
    cycle_temp = [0] * len(cycle_col)
    flag = 0
    df_len = len(filtered_df.index) - 1
    # print(filtered_df)

    for i, ds_temp in filtered_df.iterrows():
        if i + 1 <= df_len:
            ds_temp_next = filtered_df.loc[i + 1, ["time", "vac_status", "pre_status"]]
            # print(ds_temp)
            # 第一筆資料判斷
            if flag == 0 and i == 0:
                if ds_temp['vac_status'] == 1:  # 抽真空
                    flag == 1
                    print("抽真空", ds_temp["time"])
                    cycle_temp[0], cycle_temp[1] = ds_temp["time"], i

                elif ds_temp['vac_status'] == 0 and ds_temp_next['vac_status'] == 0:  # 真空維持
                    print("真空維持", ds_temp["time"])
                    flag = 2
                    cycle_temp[2], cycle_temp[3] = ds_temp["time"], i

                elif ds_temp['pre_status'] == 0 and ds_temp_next['pre_status'] > ds_temp['pre_status']:  # 加壓開始
                    print("加壓開始", ds_temp["time"])
                    flag = 3
                    cycle_temp[4], cycle_temp[5] = ds_temp["time"], i

                elif ds_temp['pre_status'] == 3:  # 加壓維持
                    print("加壓維持", ds_temp["time"])
                    flag = 4
                    cycle_temp[6], cycle_temp[7] = ds_temp["time"], i

                elif ds_temp['pre_status'] == 3 and ds_temp_next['pre_status'] == 2:  # 第一次洩壓
                    print("初次洩壓", ds_temp["time"])
                    flag = 5
                    cycle_temp[8], cycle_temp[9] = ds_temp["time"], i

                elif ds_temp_next['pre_status'] <= 2:  # 洩壓中
                    print("洩壓中", ds_temp["time"])
                    flag = 5
                    cycle_temp[8], cycle_temp[9] = ds_temp["time"], i

                elif ds_temp['pre_status'] == 1 and ds_temp_next['pre_status'] == 0:  # 完全洩壓/製程結束
                    print("製程結束", ds_temp["time"])
                    flag = 6
                    cycle_temp[10], cycle_temp[11] = ds_temp["time"], i

            # 製程開始
            elif flag == 0 and ds_temp['vac_status'] == 2 and ds_temp_next['vac_status'] == 1:
                print("製程開始", ds_temp["time"])
                flag = 1
                cycle_temp[0], cycle_temp[1] = ds_temp["time"], i

            # 真空維持
            elif flag == 1 and ds_temp['vac_status'] == 0 and ds_temp_next['vac_status'] == 0:
                print("真空維持", ds_temp["time"])
                flag = 2
                cycle_temp[2], cycle_temp[3] = ds_temp["time"], i
                cycle_temp[12] = (pd.to_datetime(cycle_temp[2]) - pd.to_datetime(cycle_temp[0])).total_seconds() / 60
            # 加壓開始
            elif flag == 2 and ds_temp['pre_status'] == 0 and ds_temp_next['pre_status'] > ds_temp['pre_status']:
                print("加壓開始", ds_temp["time"])
                flag = 3
                cycle_temp[4], cycle_temp[5] = ds_temp["time"], i
                cycle_temp[12] = cycle_temp[12] + (
                        (pd.to_datetime(cycle_temp[4]) - pd.to_datetime(cycle_temp[2])).total_seconds() / 60)
            # 加壓維持
            elif flag == 3 and ds_temp['pre_status'] == 3:
                print("加壓維持", ds_temp["time"])
                flag = 4
                cycle_temp[6], cycle_temp[7] = ds_temp["time"], i
                cycle_temp[12] = cycle_temp[12] + (
                        (pd.to_datetime(cycle_temp[6]) - pd.to_datetime(cycle_temp[4])).total_seconds() / 60)
            # 第一次洩壓
            elif flag == 4 and ds_temp['pre_status'] == 3 and ds_temp_next['pre_status'] == 2:
                print("初次洩壓", ds_temp["time"])
                flag = 5
                cycle_temp[8], cycle_temp[9] = ds_temp["time"], i
                cycle_temp[12] = cycle_temp[12] + (
                        (pd.to_datetime(cycle_temp[8]) - pd.to_datetime(cycle_temp[6])).total_seconds() / 60)
            # 完全洩壓/製程結束
            elif flag == 5 and ds_temp['pre_status'] == 1 and ds_temp_next['pre_status'] == 0:
                print("製程結束", ds_temp["time"])
                flag = 6
                cycle_temp[10], cycle_temp[11] = ds_temp["time"], i
                cycle_temp[12] = cycle_temp[12] + (
                        (pd.to_datetime(cycle_temp[10]) - pd.to_datetime(cycle_temp[8])).total_seconds() / 60)

            # 重設flag
            if flag == 6:
                print("稼動工時 : %.1f 分鐘" % cycle_temp[12])
                print("=" * 20)
                cycle = cycle.append(pd.Series(cycle_temp, index=cycle_col), ignore_index=True)
                cycle_temp = [0] * 13
                flag = 0
        else:
            l = (flag-1)*2
            # print(cycle_temp[l])
            cycle_temp[12] = cycle_temp[12] + ((pd.to_datetime(ds_temp["time"]) - pd.to_datetime(cycle_temp[l])).total_seconds() / 60)
            # print(cycle_temp)
            print("稼動工時 : %.1f 分鐘" % cycle_temp[12])
            print("=" * 20)
            cycle = cycle.append(pd.Series(cycle_temp, index=cycle_col), ignore_index=True)
            break

    # cycle.to_csv("cycle_test.csv")

    print("%s 至 %s " % (filtered_df.time[0], filtered_df.time[df_len]))

    #total_time = ((pd.to_datetime(filtered_df.time[df_len]) - pd.to_datetime(filtered_df.time[0])).total_seconds() / 60)
    total_time = 1440
    print("總開機時間 : %.1f 分鐘" % total_time)

    total_run_time = cycle.loc[:, "running_time"].sum()
    total_run_time = round(total_run_time, 1)
    print("總稼動工時 : %.1f 分鐘" % total_run_time)

    total_standby_time = total_time - total_run_time
    total_standby_time = round(total_standby_time, 1)
    print("總待機時間 : %.1f 分鐘" % total_standby_time)

    run_time_ratio = (total_run_time / total_time) * 100
    run_time_ratio = round(run_time_ratio, 1)
    print("稼動率 : %.1f" % run_time_ratio)

    standby_time_ratio = (total_standby_time / total_time) * 100
    standby_time_ratio = round(standby_time_ratio, 1)
    print("待機率 : %.1f" % standby_time_ratio)
    print("=" * 20)

    report_dict = {"日期": start_date, "稼動率(%)": run_time_ratio, "待機率(%)": standby_time_ratio, "異常率(%)": 0,
                   "稼動工時(分)": total_run_time, "待機工時(分)": total_standby_time, "異常工時(分)": 0, "總開機工時(分)": 1440}
    return report_dict


print("製程分析結束")
# 照日期切割DF子集
# 生成週間每日日期
dates = [''] * 8
for i in range(len(dates)):
    dates[i] = (start + datetime.timedelta(days=i)).strftime("%Y-%m-%d")

# print(dates)
# print(len(dates))
# 生成每日稼動分析報告DF

report_col = ["日期", "稼動率(%)", "待機率(%)", "異常率(%)", "稼動工時(分)", "待機工時(分)", "異常工時(分)", "總開機工時(分)", "備註"]
report = pd.DataFrame(columns=report_col)

for i in range(len(dates) - 1):
    dates_filtered_df = df.query("time >= '" + dates[i] + "' and time <='" + dates[i + 1] + "'")
    dates_filtered_df = dates_filtered_df.reset_index(drop=True)
    report = report.append(status_analyzer(dates_filtered_df, dates[i]), ignore_index=True)
    # print(report)

report.set_index("日期", inplace=True)
report.to_csv("report_test.csv", encoding="utf_8_sig")
'''
# 數值折線圖

fig, ax1 = plt.subplots()
plt.title('Infusion Vacuum & Pressure')
plt.xlabel('time')

ax2 = ax1.twinx()

ax1.set_ylabel('Vacuum', color='tab:blue')
ax1.plot(filtered_df.time, filtered_df.infusion_vacuum, color='blue')
ax1.tick_params(axis='y', labelcolor='tab:blue')

ax2.set_ylabel('Pressure', color='green')
ax2.plot(filtered_df.time, filtered_df.infusion_pressure, color='green')
ax2.tick_params(axis='y', labelcolor='green')

fig.tight_layout()
plt.show()


# 狀態折線圖
fig, ax3 = plt.subplots()
plt.title('Infusion Vacuum & Pressure')
plt.xlabel('time')

ax4 = ax3.twinx()

ax3.set_ylabel('vac_status', color='tab:blue')
ax3.plot(filtered_df.time, filtered_df.vac_status, color='blue')
ax3.tick_params(axis='y', labelcolor='tab:blue')

ax4.set_ylabel('pre_status', color='green')
ax4.plot(filtered_df.time, filtered_df.pre_status, color='green')
ax4.tick_params(axis='y', labelcolor='green')

fig.tight_layout()
plt.show()
'''
# writer = pd.ExcelWriter('檔名', engine = 'xlsxwriter')
writer = pd.ExcelWriter('含浸爐VPI3800設備稼動週報表.xlsx', engine='xlsxwriter')
# sheet_name 可自行命名
report.to_excel(writer, sheet_name='VPI3800')
workbook = writer.book
# 指定接下來要編輯的 sheet
worksheet = writer.sheets['VPI3800']
merge_format = workbook.add_format({
    'bold':     True,
    'border':   6,
    'align':    'center',#水平居中
    'valign':   'vcenter',#垂直居中
    'fg_color': '#ffed61',#颜色填充
})
worksheet.merge_range('J1:M1', '含浸爐-VPI3800  設備稼動週報表', merge_format)

# column 柱狀圖 area面積圖 bar 條形圖 line折現圖 radar雷達圖
column_chart = workbook.add_chart({"type": "column"})
column_chart.set_title({"name": "設備效能"})
column_chart.add_series({"name": "稼動率(%)", "categories": "=VPI3800!$a$2:$a$8", "values": "=VPI3800!$b$2:$b$8"})
column_chart.add_series({"name": "待機率(%)", "categories": "=VPI3800!$a$2:$a$8", "values": "=VPI3800!$c$2:$c$8"})
column_chart.add_series({"name": "異常率(%)", "categories": "=VPI3800!$a$2:$a$8", "values": "=VPI3800!$d$2:$d$8"})
column_chart.set_x_axis({'name': '日期'})
column_chart.set_y_axis({'name': '%'})
# column_chart.set_style(11)
worksheet.insert_chart("A11", column_chart)

line_chart = workbook.add_chart({"type": "line"})
line_chart.set_title({"name": "設備工時"})
line_chart.add_series({"name": "稼動工時(分)", "categories": "=VPI3800!$a$2:$a$8", "values": "=VPI3800!$e$2:$e$8"})
line_chart.add_series({"name": "待機工時(分)", "categories": "=VPI3800!$a$2:$a$8", "values": "=VPI3800!$f$2:$f$8"})
line_chart.add_series({"name": "異常工時(分)", "categories": "=VPI3800!$a$2:$a$8", "values": "=VPI3800!$g$2:$g$8"})
line_chart.add_series({"name": "總開機工時(分)", "categories": "=VPI3800!$a$2:$a$8", "values": "=VPI3800!$h$2:$h$8"})
line_chart.set_x_axis({'name': '日期'})
line_chart.set_y_axis({'name': '分'})
# column_chart.set_style(11)
worksheet.insert_chart("J11", line_chart)
# 存檔
writer.save()
print("報表生成完畢")

# email發送
# 預設本周要寄出上周一至周日的報告，故抓出上周一的日期
today_date = datetime.date.today()
days_to_mon = today_date.weekday()

this_mon = today_date - datetime.timedelta(days = days_to_mon)
last_mon = this_mon - datetime.timedelta(days = 7)


# read the list of recipients
f = open("list.txt")
lines = f.read().splitlines()
print(lines)

# Email Account
email_sender_account = "pythonnotificantionbot@gmail.com"  # your email
email_sender_username = "pythonnotificantionbot@gmail.com"  # your email username
email_sender_password = "tecopythonproject"  # your email password
email_smtp_server = "smtp.gmail.com"  # change if not gmail.
email_smtp_port = 587  # change if needed.
email_recepients = lines  # your recipients
f.close()

#設定信件內容與收件人資訊
Subject = "VPI3800稼動週報 ({})".format(last_mon)
contents = """
VPI3800稼動週報
""".format(last_mon)

# 設定附件（可設多個）
attachments = ['含浸爐VPI3800設備稼動週報表.xlsx']

server = smtplib.SMTP(email_smtp_server, email_smtp_port)
print(f"Logging in to {email_sender_account}")
server.starttls()
server.login(email_sender_username, email_sender_password)

for recipient in email_recepients:
    print(f"Sending email to {recipient}")
    message = MIMEMultipart()
    message['From'] = email_sender_account
    message['To'] = recipient
    message['Subject'] = Subject
    message.attach(MIMEText(contents))
    for file in attachments:
        with open(file, 'rb') as fp:
            add_file = MIMEBase('application', "octet-stream")
            add_file.set_payload(fp.read())
            encoders.encode_base64(add_file)
            add_file.add_header('Content-Disposition', 'attachment', filename='含浸爐VPI3800設備稼動週報表.xlsx')
            message.attach(add_file)
    server.sendmail(email_sender_account, recipient, message.as_string())


server.quit()
print("信件發送成功")
