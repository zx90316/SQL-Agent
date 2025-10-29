「SQL Server 自然語言查詢工具」開發文件1. 專案概觀1.1. 目的本專案旨在建立一個內部網頁應用程式，允許使用者透過自然語言（例如：「查詢昨天所有A產品的訂單」）來查詢 SQL Server 資料庫。1.2. 核心架構前端 (Frontend): 使用者在 HTML 頁面輸入查詢。後端 (Backend): FastAPI 應用程式接收請求。LLM 服務 (LLM Service): 後端將使用者的自然語言查詢，連同相關的資料庫結構(Schema)資訊，發送到 Google Cloud Vertex AI。資料庫 (Database): LLM 僅回傳 SQL 查詢語法字串。後端執行此 SQL 語法，並將查詢結果回傳給前端。1.3. 關鍵隱私限制依照需求，資料庫中回傳的任何「資料」 (Data) 絕對不會被傳送到 Vertex AI (LLM)。LLM 的唯一任務是「生成 SQL 語法」，它對資料庫的實際內容保持未知。(註：本工具是一個獨立的 Web 應用程式，用於查詢 SQL Server。它與 "SQL Server Agent" (作業排程器) 的功能不同，但可以查詢由 Agent 維護或管理的資料庫。)2. 技術棧 (Technology Stack)組件技術版本/備註後端框架FastAPIPython 3.11前端HTML, CSS(搭配少量 JavaScript 進行 API 呼叫)LLM 服務Google Cloud Vertex AI(例如 PaLM 2 或 Gemini Mdoels)資料庫Microsoft SQL Server-Python DB 驅動pyodbc 或 sqlalchemy-Python K/Vgoogle-cloud-aiplatform用於連接 Vertex AI3. 系統架構與資料流程程式碼片段graph TD
    subgraph "使用者瀏覽器"
        A[HTML/CSS/JS 前端]
    end

    subgraph "後端伺服器 (FastAPI)"
        B[API Endpoint: /query]
        C[SQL 驗證器 (Security)]
        D[資料庫連線 (pyodbc)]
    end

    subgraph "Google Cloud"
        E[Vertex AI (LLM)]
    end

    subgraph "資料庫伺服器"
        F[MS SQL Server]
    end

    A -- 1. 輸入自然語言 (JSON) --> B
    B -- 2. 準備 Prompt (NL + Schema) --> E
    E -- 3. 回傳 SQL 語法 (String) --> B
    B -- 4. 驗證 SQL (e.g., 僅 SELECT) --> C
    C -- 5. 執行安全的 SQL --> D
    D -- 6. 查詢 --> F
    F -- 7. 回傳資料結果 (Rows) --> D
    D -- 8. 組合資料 --> B
    B -- 9. 回傳資料 (JSON) --> A
    A -- 10. 渲染成 HTML 表格 --> A

    style E fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#f9f,stroke:#333,stroke-width:2px
4. 核心工作流程 (Workflow)使用者輸入 (Frontend):使用者在 <textarea> 中輸入「顯示最近 5 筆登入失敗的紀錄」。點擊「查詢」按鈕。JavaScript 將此字串打包成 JSON {"nl_query": "..."}，並 fetch 到後端的 /api/query 端點。Schema 準備 (Backend):後端 API 接收到請求。為了讓 LLM 知道如何撰寫 SQL，後端必須提供資料庫結構 (Schema)。(建議) 從一個設定檔或快取中讀取預先定義好的、允許被查詢的 Table/Column 資訊（例如 CREATE TABLE ... 語法）。LLM 提示 (Backend -> Vertex AI):後端組合一個 Prompt，發送給 Vertex AI。Prompt 範例:程式碼片段你是一個 SQL Server 專家。
根據以下的資料庫結構 (Schema)：

[
    CREATE TABLE Users (
        UserID INT PRIMARY KEY,
        Username VARCHAR(50),
        LastLogin DATETIME
    );
    CREATE TABLE LoginLogs (
        LogID INT PRIMARY KEY,
        UserID INT,
        LoginTime DATETIME,
        Success BIT,
        IPAddress VARCHAR(50)
    );
]

請將以下使用者的自然語言請求，轉換為一個安全的、僅供讀取 (read-only) 的 T-SQL (SQL Server) 查詢語法。
- 絕對不可以使用 UPDATE, DELETE, INSERT, DROP, EXEC。
- 只回傳 SQL 語法，不要有任何額外的說明文字。

使用者請求: "顯示最近 5 筆登入失敗的紀錄"

SQL 查詢:
LLM 回應 (Vertex AI -> Backend):Vertex AI 只會回傳一個字串，例如：SELECT TOP 5 * FROM LoginLogs WHERE Success = 0 ORDER BY LoginTime DESC安全驗證 (Backend):[極度重要] 後端收到 SQL 字串後，必須進行安全驗證。這是一個「防護欄」，防止 LLM 產生惡意或破壞性的語法。最小驗證: 檢查語法是否以 SELECT 開頭，並確保不包含 UPDATE, DELETE, INSERT, DROP, TRUNCATE, EXEC 等關鍵字。資料庫執行 (Backend -> DB):驗證通過後，後端使用 pyodbc 執行此 SQL 查詢。[安全建議] 用於執行此查詢的資料庫帳號，應僅有 db_datareader (唯讀) 權限。回傳資料 (Backend -> Frontend):資料庫回傳查詢結果 (例如：一個 row 列表)。FastAPI 將此結果序列化為 JSON 格式，回傳給前端。(再次強調：此 JSON 資料 不會 被傳送到 Vertex AI)顯示結果 (Frontend):前端 JavaScript 收到 JSON 陣列。動態生成一個 HTML <table>，包含表頭 (<thead>) 和資料列 (<tbody>)，將結果顯示給使用者。5. 關鍵組件開發 (FastAPI + Python)5.1. 專案結構 (建議)/sql_nl_query
|-- /app
|   |-- __init__.py
|   |-- main.py         # FastAPI 應用程式主體
|   |-- vertex_client.py # 處理 Vertex AI 呼叫的邏輯
|   |-- db_handler.py   # 處理 SQL Server 連線與查詢
|   |-- security.py     # SQL 驗證邏輯
|   |-- schema.py       # (或 schema.txt) 存放資料庫結構
|
|-- /static             # 存放 HTML/CSS
|   |-- index.html
|   |-- style.css
|   |-- script.js
|
|-- requirements.txt
|-- .env              # 存放資料庫連線字串、GCP 金鑰路徑
5.2. main.py (FastAPI 端點範例)Pythonimport os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any

# 匯入自定義模組
from . import vertex_client, db_handler, security, schema

app = FastAPI()

class QueryRequest(BaseModel):
    nl_query: str

# 掛載靜態文件 (HTML/CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post("/api/query")
async def handle_query(request: QueryRequest) -> Dict[str, Any]:
    
    # 1. 取得資料庫結構 (Schema)
    db_schema = schema.get_db_schema()

    # 2. 呼叫 Vertex AI 生成 SQL
    try:
        sql_query = await vertex_client.generate_sql_from_nl(
            nl_query=request.nl_query,
            schema_info=db_schema
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {e}")

    # 3. [關鍵] 安全驗證 SQL
    if not security.is_safe_sql(sql_query):
        raise HTTPException(status_code=400, detail="Generated SQL query is not safe.")

    # 4. 執行 SQL 並取得資料
    try:
        columns, rows = await db_handler.execute_query(sql_query)
        
        # 5. 回傳結果
        return {
            "query_generated": sql_query,
            "columns": columns,
            "data": rows
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Error: {e}")

5.3. vertex_client.py (Vertex AI 呼叫)Pythonfrom google.cloud import aiplatform
from google.oauth2 import service_account

# ... (初始化 Vertex AI 客戶端) ...

async def generate_sql_from_nl(nl_query: str, schema_info: str) -> str:
    # 這裡使用 Vertex AI SDK
    # ... (設定 Project, Location) ...

    # 組合 Prompt
    prompt = f"""
    你是一個 SQL Server 專家。
    根據以下的資料庫結構 (Schema)：
    {schema_info}

    請將以下使用者的自然語言請求，轉換為一個安全的、僅供讀取 (read-only) 的 T-SQL (SQL Server) 查詢語法。
    - 絕對不可以使用 UPDATE, DELETE, INSERT, DROP, EXEC。
    - 只回傳 SQL 語法，不要有任何額外的說明文字。

    使用者請求: "{nl_query}"

    SQL 查詢:
    """

    # ... (呼叫 Vertex AI 的 text-generation or chat model) ...
    
    # 假設 model.predict() 回傳了結果
    response_text = "SELECT TOP 5 * FROM LoginLogs WHERE Success = 0 ORDER BY LoginTime DESC" # 模擬回應
    
    # 清理回應 (去除 LLM 可能多加的 "```sql" 等)
    sql_query = response_text.strip().replace("```sql", "").replace("```", "")
    
    return sql_query
5.4. security.py (SQL 驗證)Pythonimport re

# 黑名單中的危險關鍵字
DANGEROUS_KEYWORDS = [
    'INSERT', 'UPDATE', 'DELETE', 'DROP', 'TRUNCATE', 'ALTER', 'CREATE', 
    'EXEC', 'EXECUTE', 'MERGE', 'GRANT', 'REVOKE', 'sp_executesql'
]

def is_safe_sql(sql_query: str) -> bool:
    query_upper = sql_query.upper()

    # 1. 必須以 SELECT 開頭
    if not query_upper.strip().startswith('SELECT'):
        return False

    # 2. 檢查是否包含危險關鍵字 (使用正則表達式確保是獨立單字)
    for keyword in DANGEROUS_KEYWORDS:
        if re.search(r'\b' + keyword + r'\b', query_upper):
            return False
            
    # 3. 檢查是否有多重語句
    if ';' in query_upper.strip()[:-1]: # 允許結尾的分號
        return False

    return True

6. 前端 (HTML/CSS/JS)6.1. static/index.htmlHTML<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <title>自然語言查詢</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h2>SQL Server 自然語言查詢</h2>
        <textarea id="nl-input" rows="4" placeholder="請輸入您的查詢... (例如：顯示 5 筆最新的使用者登入紀錄)"></textarea>
        <button id="submit-btn">查詢</button>
        
        <div id="loading" style="display:none;">處理中...</div>
        <div id="error-msg" class="error"></div>
        
        <h3>查詢結果:</h3>
        <div id="results-container">
            </div>
    </div>
    <script src="script.js"></script>
</body>
</html>
6.2. static/script.js (前端邏輯)JavaScriptdocument.getElementById('submit-btn').addEventListener('click', async () => {
    const query = document.getElementById('nl-input').value;
    const resultsContainer = document.getElementById('results-container');
    const errorMsg = document.getElementById('error-msg');
    const loading = document.getElementById('loading');

    // 清空舊結果
    resultsContainer.innerHTML = '';
    errorMsg.textContent = '';
    loading.style.display = 'block';

    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nl_query: query })
        });

        loading.style.display = 'none';

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || '查詢失敗');
        }

        const result = await response.json();
        renderTable(result.columns, result.data);

    } catch (err) {
        loading.style.display = 'none';
        errorMsg.textContent = err.message;
    }
});

function renderTable(columns, data) {
    const container = document.getElementById('results-container');
    if (!data || data.length === 0) {
        container.innerHTML = '<p>查無資料。</p>';
        return;
    }

    const table = document.createElement('table');
    
    // 表頭 (thead)
    const thead = table.createTHead();
    const headerRow = thead.insertRow();
    columns.forEach(colName => {
        const th = document.createElement('th');
        th.textContent = colName;
        headerRow.appendChild(th);
    });

    // 資料 (tbody)
    const tbody = table.createTBody();
    data.forEach(rowData => {
        const row = tbody.insertRow();
        rowData.forEach(cellData => {
            const cell = row.insertCell();
            cell.textContent = cellData;
        });
    });

    container.appendChild(table);
}