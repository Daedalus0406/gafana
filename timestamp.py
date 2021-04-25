import time

def timestamp_datetime(value):
    format = '%Y-%m-%d %H:%M:%S'
# value為傳入的值為時間戳(整形)，如：1332888820
    t_value = time.localtime(value)
## 經過localtime轉換後變成
## time.struct_time(tm_year=2012, tm_mon=3, tm_mday=28, tm_hour=6, tm_min=53, tm_sec=40, tm_wday=2, tm_yday=88, tm_isdst=0)
# 最後再經過strftime函式轉換為正常日期格式。
    dt = time.strftime(format, t_value)
    print(type(value))
    print(type(t_value))
    print(type(dt))

    return dt


s = timestamp_datetime(1332888820)
print (s)
