# backtest_ma.py

import backtrader as bt
import pandas as pd
import datetime


class MaCrossStrategy(bt.Strategy):
    params = (
        ("ma_short", 12),      # 12日均线
        ("ma_long", 26),       # 26日均线
        ("slippage", 0.0001),  # 万分之一的滑点(可在这里或外部设置)
    )

    def __init__(self):
        """
        初始化指标：12日均线 & 26日均线
        以及判断均线交叉的CrossOver指示器
        """
        self.ma_short = bt.indicators.MovingAverageSimple(
            self.datas[0].close, period=self.params.ma_short
        )
        self.ma_long = bt.indicators.MovingAverageSimple(
            self.datas[0].close, period=self.params.ma_long
        )
        self.crossover = bt.indicators.CrossOver(self.ma_short, self.ma_long)

    def next(self):
        """
        每个交易日都会执行该函数，
        在这里根据策略逻辑判断是否买卖
        """
        # 1) 12日均线上穿26日均线 -> 买入
        if self.crossover[0] == 1:
            # 每次买入资金为总资金的 20%
            total_value = self.broker.getvalue()  # 当前总资金（现金+市值）
            buy_cash = total_value * 0.2

            if buy_cash > 0:
                # 计算买入股数（取整）
                size = int(buy_cash / self.data.close[0])
                if size > 0:
                    self.buy(size=size)

        # 2) 当价格跌破26日均线 -> 卖出
        if self.data.close[0] < self.ma_long[0]:
            # 如果当前有持仓，就全部平仓
            if self.position.size > 0:
                self.sell(size=self.position.size)


def run_backtest(csv_path,
                 start_date="2023-01-01",
                 end_date="2023-12-31"):
    """
    从 csv 文件读取数据，根据传入的 start_date ~ end_date 动态设置回测区间，
    并使用 MaCrossStrategy 策略进行回测。

    :param csv_path: CSV 文件路径
    :param start_date: 回测起始日期 (格式: YYYY-MM-DD)
    :param end_date:   回测结束日期 (格式: YYYY-MM-DD)
    :return: dict, 示例: { "收益率": 0.1234, "总权益": 1123456.78 }
    """

    # 1) 初始化Cerebro
    cerebro = bt.Cerebro()

    # 2) 设置初始资金
    initial_cash = 1_000_000
    cerebro.broker.setcash(initial_cash)

    # 3) 设置滑点(万分之一) - 在backtrader里通常用commission/slippage模块
    # 这里示例用 commission 近似模拟
    cerebro.broker.setcommission(commission=0.0001)

    # 4) 读取 CSV 数据
    df = pd.read_csv(csv_path)

    # 确保日期正确顺序(一般Tushare返回是倒序，需要升序)
    df.sort_values("trade_date", inplace=True)

    # 转换 trade_date 为 datetime 对象，并设置为索引
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
    df.set_index("trade_date", inplace=True)

    # 5) 将 start_date, end_date 转换为 datetime
    #    假设传入格式是 YYYY-MM-DD
    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    # 6) 构建 Backtrader 数据源，动态设置 fromdate / todate
    data = bt.feeds.PandasData(
        dataname=df,
        fromdate=start_dt,
        todate=end_dt,
        open='open',
        high='high',
        low='low',
        close='close',
        volume='vol',      # Tushare的成交量字段为 vol
        openinterest=None  # 没有持仓量就设为 None
    )

    # 7) 将数据和策略加载到Cerebro
    cerebro.adddata(data)
    cerebro.addstrategy(MaCrossStrategy)

    # 8) 运行回测
    cerebro.run()

    # 9) 获取回测后的最终资产总值
    final_value = cerebro.broker.getvalue()
    total_return = (final_value / initial_cash) - 1

    # 10) 输出结果
    result = {
        "收益率": round(total_return, 4),  # 保留4位小数
        "总权益": round(final_value, 2)
    }
    return result


if __name__ == "__main__":
    # 测试时，可手动指定一个区间
    results = run_backtest(
        csv_path="pingan.csv", 
        start_date="2023-01-01", 
        end_date="2023-12-31"
    )
    print("回测结果：", results)
    # 示例输出：{'收益率': 0.1023, '总权益': 1102345.67}
