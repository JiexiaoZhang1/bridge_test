# fetch_data.py
import tushare as ts

# 第一步：设置token
ts.set_token("69b82cdb474c9a4bb81820feaa02b3742428ecfb72159180eb0ef7aa")  # 替换成你的有效token
pro = ts.pro_api()

data = pro.query('stock_basic', exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
data.to_csv("STOCK_MAP.csv", index=False)
print("数据获取完毕，已保存为 pingan.csv！")
