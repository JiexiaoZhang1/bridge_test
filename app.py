import os
import datetime
import tushare as ts
import pandas as pd

from flask import Flask, request, jsonify
from flask_cors import CORS

# 假设你把回测逻辑写在 backtest/backtest_ma.py
from backtest.backtest_ma import run_backtest

app = Flask(__name__)
CORS(app)

# 全局变量，存储最新一次回测的结果
backtest_result = {}

# ========== 1) 读取 STOCK_MAP.csv 并构建 name->ts_code 的映射 ==========

# 说明：
# - CSV 格式：ts_code,symbol,name,area,industry,list_date
# - 我们只关心 name 和 ts_code
# - 如果 CSV 文件很多行，就完整读取，然后在内存里做字典映射

STOCK_MAP_DF = pd.read_csv("STOCK_MAP.csv")  # 路径根据实际情况
# 构建字典 {股票名称: ts_code}
NAME_TO_TSCODE = dict(zip(STOCK_MAP_DF["name"], STOCK_MAP_DF["ts_code"]))

# 如果你想让用户也能用 'symbol' 或者其他字段来匹配，也可以再建一个映射
# 这里示例只做 name -> ts_code

# ========== 2) 配置 Tushare Token ==========

# 建议从环境变量获取，或写在此处（请注意保密）
TS_TOKEN = "69b82cdb474c9a4bb81820feaa02b3742428ecfb72159180eb0ef7aa"
ts.set_token(TS_TOKEN)
pro = ts.pro_api()


@app.route("/set_backtest", methods=["POST"])
def set_backtest():
    """
    接收 JSON 格式:
    {
      "stock": "平安银行",
      "start_date": "2023-01-01",
      "end_date": "2023-12-31"
    }
    然后从 Tushare 动态下载对应区间的数据，执行回测。
    """
    data = request.json
    stock_name = data.get("stock", "平安银行")
    start_date_str = data.get("start_date", "2023-01-01")
    end_date_str = data.get("end_date", "2023-12-31")

    # 1) 将前端传来的日期字符串 "YYYY-MM-DD" 转为 "YYYYMMDD"
    start_date_fmt = start_date_str.replace("-", "")
    end_date_fmt = end_date_str.replace("-", "")

    # 2) 根据 stock_name 查找对应 ts_code
    #    如果 STOCK_MAP.csv 没有该名字，就默认用 "000001.SZ" 或者返回错误
    ts_code = NAME_TO_TSCODE.get(stock_name, "000001.SZ")

    # 3) 从 Tushare 下载对应时间区间的日线数据
    df = pro.daily(ts_code=ts_code, start_date=start_date_fmt, end_date=end_date_fmt)

    if df.empty:
        return jsonify({
            "msg": f"未从 Tushare 获取到股票[{stock_name}]在[{start_date_str}~{end_date_str}]的行情数据，检查名称或日期。",
            "stock": stock_name,
            "start_date": start_date_str,
            "end_date": end_date_str
        }), 400

    # 4) 将数据保存到临时 CSV（或直接传 DataFrame 给回测）
    df.sort_values("trade_date", inplace=True)
    csv_path = "temp_backtest_data.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")

    # 5) 执行回测
    result = run_backtest(
        csv_path=csv_path,
        start_date=start_date_str,
        end_date=end_date_str
    )

    # 6) 更新全局 backtest_result
    backtest_result["收益率"] = result["收益率"]
    backtest_result["总权益"] = result["总权益"]

    return jsonify({
        "msg": "回测完成",
        "stock": stock_name,
        "ts_code": ts_code,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "回测结果": backtest_result
    }), 200


@app.route("/result", methods=["GET"])
def get_result():
    """
    返回最近一次回测结果
    """
    if not backtest_result:
        return jsonify({"msg": "尚未进行回测或无结果"}), 400

    return jsonify({
        "收益率": backtest_result.get("收益率"),
        "总权益": backtest_result.get("总权益")
    }), 200


if __name__ == "__main__":
    # 启动服务
    app.run(debug=True, port=8000)
