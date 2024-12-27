1. **项目简介**  
2. **环境安装与依赖**  
3. **项目文件结构**  
4. **如何获取股票映射文件 (STOCK_MAP.csv)**  
5. **如何运行回测后端 (app.py)**  
6. **API 文档**  
7. **前端测试示例 (index.html)**  
8. **其他调试方法**  
9. **常见问题排查**  

---

# README

## 1. 项目简介

本项目演示了以下功能：

- **动态获取沪深市场的股票列表** 并保存为 `STOCK_MAP.csv`，用于映射“股票名称”到 `ts_code`。  
- **动态下载目标股票在指定日期区间内的日线数据**（基于 [Tushare](https://tushare.pro/)），然后用 **Backtrader** 做回测。  
- **策略逻辑**：使用 12 日/26 日均线交叉策略，当 12 日均线上穿 26 日均线时买入（占用总资金的 20%），当收盘价跌破 26 日均线时卖出全部持仓。  
- **后端 API**：使用 Flask 提供两个接口：
  1. `POST /set_backtest`：设置要回测的股票与时间区间，并执行回测  
  2. `GET /result`：返回最近一次回测结果（收益率、总权益）  
- **前端测试页面 (index.html)**：在浏览器打开，可填写股票名称及日期，点击后端运行回测，并查看结果。

---

## 2. 环境安装与依赖

### 2.1 Python 版本

建议 Python 3.7 以上（3.9/3.10 都可）。

### 2.2 第三方库

项目需要以下主要依赖：

- **tushare**：获取股票基础信息、行情数据  
- **backtrader**：回测框架  
- **flask**：提供后端 API  
- **flask-cors**：解决跨域请求问题  
- **pandas**：数据处理  
- 其他常见库如 `datetime`、`requests` 可使用标准库或按需安装。


---

## 3. 项目文件结构

```
bridge_test/
├── app.py                         # Flask后端，提供 /set_backtest 与 /result 两个接口
├── backtest/
│   ├── __init__.py
│   └── backtest_ma.py             # 12/26均线策略 & run_backtest函数
├── fetch_data.py                  # 从Tushare获取股票列表并保存为 STOCK_MAP.csv
├── index.html                     # 前端测试页面，可通过浏览器进行回测请求
├── prompt.txt                     # 和AI的对话
├── README.md                      # 你现在看到的文档
├── STOCK_MAP.csv                  # 股票映射表（ts_code, name 等）
└── temp_backtest_data.csv         # 动态下载后暂存的行情数据文件（可随时被覆盖）
```

说明：

- **`fetch_data.py`**：把所有上市股票基础信息拉到 `STOCK_MAP.csv`，其中包含 `ts_code,name` 等。  
- **`STOCK_MAP.csv`**：后续由 `app.py` 读取，用于根据“股票名称”找到对应 `ts_code`。  
- **`app.py`**：核心后端逻辑，包含：
  - 读取/加载 `STOCK_MAP.csv` -> 构建 `NAME_TO_TSCODE` 映射  
  - `POST /set_backtest` -> 根据传入的 `stock`、起止日期，下载行情数据 -> 调用 `run_backtest` -> 缓存回测结果  
  - `GET /result` -> 返回缓存结果  
- **`backtest_ma.py`**：基于 Backtrader 实现 12/26 均线策略，并提供 `run_backtest` 函数，能够按照传入的时间区间进行回测。  
- **`index.html`**：浏览器端简单表单，可输入股票名称与日期，提交后跳转 `/result` 查看回测结果。

---

## 4. 如何获取股票映射文件 (STOCK_MAP.csv)

1. 在命令行中执行：

   ```bash
   python fetch_data.py
   ```
2. 脚本示例（简化）如下：

   ```python
   # fetch_data.py
   import tushare as ts

   # 设置token
   ts.set_token("YOUR_TUSHARE_TOKEN_HERE") 
   pro = ts.pro_api()

   # 获取所有正常上市股票信息
   data = pro.query('stock_basic', exchange='', list_status='L',
                    fields='ts_code,symbol,name,area,industry,list_date')
   data.to_csv("STOCK_MAP.csv", index=False)
   print("STOCK_MAP.csv 数据获取完毕！")
   ```

3. 结果：  
   - 会在当前目录生成一个 `STOCK_MAP.csv` 文件，结构类似：  
     ```
     ts_code,symbol,name,area,industry,list_date
     000001.SZ,000001,平安银行,深圳,银行,19910403
     000002.SZ,000002,万科A,深圳,全国地产,19910129
     000004.SZ,000004,国华网安,深圳,软件服务,19910114
     ...
     ```
   - 后续 `app.py` 会用这个文件做“股票名称” -> “ts_code” 的映射。

---

## 5. 如何运行回测后端 (app.py)

1. **准备**：  
   - 保证 `STOCK_MAP.csv` 已经生成并位于 `app.py` 同级目录。  
   - 在系统环境变量或代码中设置好 Tushare Token。  
2. **启动后端**：  
   ```bash
   python app.py
   ```
   如果运行成功，你会看到 Flask 提示：  
   ```
   * Serving Flask app 'app'
   * Running on http://127.0.0.1:8000
   ```
3. **后端逻辑**（概述）  
   - **读取 `STOCK_MAP.csv`** -> 构建 `NAME_TO_TSCODE` 字典  
   - 当收到 `POST /set_backtest` 请求时：
     1. 根据前端传入的股票名称，在 `NAME_TO_TSCODE` 里找对应 `ts_code`  
     2. 结合传入的起止日期，用 Tushare 下载行情  
     3. 保存到临时文件 `temp_backtest_data.csv`  
     4. 调用 `run_backtest(csv_path, start_date, end_date)` 执行回测  
     5. 缓存回测结果  
   - 当收到 `GET /result` 请求时：返回刚才缓存的回测结果。

---

## 6. API 文档

### 6.1 POST `/set_backtest`

- **请求方法**: `POST`  
- **Content-Type**: `application/json`  
- **请求示例**:  

  ```json
  {
    "stock": "平安银行",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  }
  ```
  - `stock`: 股票中文名称（须与 `STOCK_MAP.csv` 里 name 列匹配）。例如“平安银行”、“万科A”等。  
  - `start_date`、`end_date`: 回测起止日期（格式：YYYY-MM-DD）。

- **返回示例** (JSON)：
  ```json
  {
    "msg": "回测完成",
    "stock": "平安银行",
    "ts_code": "000001.SZ",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "回测结果": {
      "收益率": -0.0028,
      "总权益": 997171.59
    }
  }
  ```
  具体数值取决于实际行情与策略执行结果。

---

### 6.2 GET `/result`

- **请求方法**: `GET`  
- **请求示例**:  
  ```
  GET http://127.0.0.1:8000/result
  ```
- **返回示例** (JSON):
  ```json
  {
    "收益率": -0.0028,
    "总权益": 997171.59
  }
  ```
  如果之前未执行 `/set_backtest` 或执行失败，可能返回 400 或空结果。

---

## 7. 前端测试示例 (index.html)

如果你想在浏览器里直接操作，可使用 `index.html` 做一个简单表单：

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>回测参数设置</title>
</head>
<body>
  <h1>回测参数设置</h1>
  <form id="backtestForm">
    <label>股票名称:</label>
    <input type="text" id="stock" value="平安银行"><br><br>

    <label>开始日期:</label>
    <input type="date" id="start_date" value="2023-01-01"><br><br>

    <label>结束日期:</label>
    <input type="date" id="end_date" value="2023-12-31"><br><br>

    <button type="submit">回测</button>
  </form>

  <script>
  document.getElementById('backtestForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const stock = document.getElementById('stock').value;
    const startDate = document.getElementById('start_date').value;
    const endDate = document.getElementById('end_date').value;

    fetch('http://127.0.0.1:8000/set_backtest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stock, start_date: startDate, end_date: endDate })
    })
      .then(res => res.json())
      .then(data => {
        console.log('回测完成:', data);
        window.location.href = 'http://127.0.0.1:8000/result';
      })
      .catch(err => console.error('回测请求失败:', err));
  });
  </script>
</body>
</html>
```

1. 双击打开 `index.html`，填写想回测的股票名称与日期；  
2. 点击“回测”，会发起 `POST /set_backtest`，成功后跳转到 `GET /result`；  
3. 如果碰到跨域问题，请确认 `app.py` 里已经 `from flask_cors import CORS` 并在 `app = Flask(__name__)` 后 `CORS(app)`。

---

## 8. 其他调试方法

### 8.1 使用 Postman / ThunderClient

1. **POST 请求**:  
   - URL: `http://127.0.0.1:8000/set_backtest`  
   - Body (raw, JSON):
     ```json
     {
       "stock": "平安银行",
       "start_date": "2023-01-01",
       "end_date": "2023-12-31"
     }
     ```
   - 点击 Send，查看响应。
2. **GET 请求**:  
   - URL: `http://127.0.0.1:8000/result`  
   - 查看返回的JSON。

### 8.2 使用命令行 `curl`

```bash
# 发起 POST
curl -X POST http://127.0.0.1:8000/set_backtest \
     -H "Content-Type: application/json" \
     -d '{
       "stock": "平安银行",
       "start_date": "2023-01-01",
       "end_date": "2023-12-31"
     }'

# 查看结果
curl http://127.0.0.1:8000/result
```

### 8.3 Python requests

```python
import requests

# set_backtest
resp = requests.post("http://127.0.0.1:8000/set_backtest", json={
    "stock": "平安银行",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
})
print(resp.json())

# result
resp2 = requests.get("http://127.0.0.1:8000/result")
print(resp2.json())
```

---

## 9. 常见问题排查

1. **`STOCK_MAP.csv` 读不到**  
   - 确认 `STOCK_MAP.csv` 与 `app.py` 在同级目录，或者在 `app.py` 里写了正确的相对/绝对路径。  
   - 确认已经通过 `fetch_data.py` 生成了该文件。

2. **提示 Token 无效或下载不到数据**  
   - 检查 Tushare Token 是否正确；  
   - 检查积分是否足够，或网络连接是否正常；  
   - 如果 `df.empty` 说明没获取到数据，可能是日期不在交易区间或 Token 失效。

3. **浏览器发请求报跨域**  
   - 需要在 Flask 中加 `CORS(app)`；  
   - 或使用 Postman / curl 调试。

4. **回测日期不变**  
   - 确认后端 `backtest_ma.py` 中已将 `start_date/end_date` 动态传给 `bt.feeds.PandasData(fromdate=..., todate=...)`。  
   - 确认后端确实拿到前端传的日期并传给 `run_backtest()`。

5. **策略无交易**  
   - 可能行情条件不满足；  
   - 检查 12/26 均线逻辑；  
   - 检查 CSV 排序与日期范围内是否有交易数据。


---


- **Clone 或 Fork** 本项目后，先用 `fetch_data.py` 生成 `STOCK_MAP.csv`；  
- **启动后端**： `python app.py`；  
- 使用 **index.html** / **Postman** / **curl** 发起请求到 `POST /set_backtest`；  
- 再用 `GET /result` 查看回测结果。  

祝你一切顺利！如有疑问，可再查看本项目的源码或查看 Tushare、Backtrader、Flask 文档以获取更多帮助。