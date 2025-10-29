# SQL Server 自然語言查詢工具

🔍 使用自然語言查詢 SQL Server 資料庫的 Web 應用程式，支援 Google Cloud Vertex AI 或本地 Ollama。

## 📋 專案概述

這是一個內部 Web 應用程式，讓使用者能夠使用中文或英文的自然語言來查詢 SQL Server 資料庫。系統支援兩種 LLM 提供者：

- **Vertex AI** - Google Cloud Vertex AI (Gemini 系列模型)
- **Ollama** - 本地部署的開源 LLM (Llama, Qwen, Mistral 等)

系統將自然語言轉換為 SQL 查詢，並嚴格執行安全控制以確保唯讀存取和資料隱私。

### 🔐 核心安全特性

- **唯讀查詢**：只允許 SELECT 語句
- **SQL 驗證**：多層安全檢查，防止惡意 SQL
- **隱私保護**：資料庫資料絕不傳送至 Vertex AI
- **最小權限**：資料庫帳號僅需 `db_datareader` 權限

## 🏗️ 技術架構

```
┌─────────────────┐
│   使用者瀏覽器   │
│  (HTML/CSS/JS)  │
└────────┬────────┘
         │ 1. 自然語言查詢
         ▼
┌─────────────────┐
│  FastAPI 後端    │
│  - API 端點      │
│  - SQL 驗證      │
│  - 資料庫連線    │
└─┬─────────────┬─┘
  │             │
  │ 2. Schema   │ 4. 執行 SQL
  │ + NL Query  │
  ▼             ▼
┌──────────┐  ┌──────────────┐
│Vertex AI │  │ SQL Server   │
│(Gemini)  │  │ Database     │
└──────────┘  └──────────────┘
  │
  │ 3. SQL 語法
  ▼
```

## 🚀 快速開始

### 環境需求

- Python 3.11+
- SQL Server (任何版本)
- ODBC Driver 17 for SQL Server
- **選擇一項 LLM 提供者：**
  - **Vertex AI**: Google Cloud 帳號 (啟用 Vertex AI API)
  - **Ollama**: 本地安裝 Ollama

### 安裝步驟

1. **複製專案**

```bash
git clone <repository-url>
cd SQL-Agent
```

2. **安裝相依套件**

```bash
pip install -r requirements.txt
```

3. **設定環境變數**

複製 `.env.example` 為 `.env` 並填入您的設定：

```bash
cp .env.example .env
```

編輯 `.env` 檔案：

```env
# 資料庫設定
DB_SERVER=your-sql-server-host
DB_NAME=your-database-name
DB_USER=your-readonly-username
DB_PASSWORD=your-password
DB_DRIVER=ODBC Driver 17 for SQL Server

# LLM 提供者選擇 (vertexai 或 ollama)
LLM_PROVIDER=vertexai

# Vertex AI 設定 (當 LLM_PROVIDER=vertexai)
GOOGLE_CLOUD_API_KEY=your-google-cloud-api-key
VERTEX_MODEL=gemini-2.5-flash

# Ollama 設定 (當 LLM_PROVIDER=ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# 應用程式設定
APP_HOST=0.0.0.0
APP_PORT=8000
```

4. **設定 LLM 提供者**

#### 選項 A: 使用 Vertex AI

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立或選擇專案
3. 啟用 Vertex AI API
4. 建立 API 金鑰
5. 設定環境變數：
   ```env
   LLM_PROVIDER=vertexai
   GOOGLE_CLOUD_API_KEY=your-api-key
   VERTEX_MODEL=gemini-2.5-flash
   ```

#### 選項 B: 使用 Ollama

1. 安裝 Ollama：[https://ollama.ai](https://ollama.ai)
2. 下載模型：
   ```bash
   ollama pull llama3.1:8b
   # 或其他模型：qwen2.5:32b, mistral:7b, deepseek-coder:33b
   ```
3. 啟動 Ollama 服務（通常會自動啟動）
4. 設定環境變數：
   ```env
   LLM_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.1:8b
   ```

5. **設定資料庫結構 (Schema)**

編輯 `app/schema.py`，將 `DEFAULT_SCHEMA` 替換為您的實際資料庫結構：

```python
DEFAULT_SCHEMA = """
CREATE TABLE YourTable (
    Column1 INT PRIMARY KEY,
    Column2 NVARCHAR(100),
    ...
);
"""
```

6. **啟動應用程式**

```bash
python -m app.main
```

或使用 uvicorn：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

7. **開啟瀏覽器**

前往 `http://localhost:8000` 開始使用！

## 📖 使用方式

### Web 介面

1. 在文字框輸入您的自然語言查詢，例如：
   - "顯示最近 10 筆訂單"
   - "查詢昨天登入失敗的使用者"
   - "列出庫存少於 10 的產品"

2. 點擊「查詢」按鈕

3. 查看生成的 SQL 語法和查詢結果

4. 可以複製 SQL 或匯出結果為 CSV

### API 端點

#### POST `/api/query`

查詢資料庫：

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"nl_query": "顯示最近 5 筆訂單"}'
```

回應：

```json
{
  "query_generated": "SELECT TOP 5 * FROM Orders ORDER BY OrderDate DESC",
  "columns": ["OrderID", "UserID", "OrderDate", "TotalAmount", "Status"],
  "data": [
    [1001, 123, "2024-01-15T10:30:00", 1500.00, "Pending"],
    ...
  ],
  "row_count": 5
}
```

#### GET `/health`

健康檢查：

```bash
curl http://localhost:8000/health
```

#### GET `/api/schema`

取得資料庫結構資訊：

```bash
curl http://localhost:8000/api/schema
```

## 🔄 LLM 提供者比較

| 特性 | Vertex AI | Ollama |
|------|-----------|--------|
| **部署** | 雲端服務 | 本地部署 |
| **成本** | 按使用量計費 | 免費（需自備硬體） |
| **效能** | 高效能、低延遲 | 取決於本地硬體 |
| **模型品質** | Gemini 系列（最新） | 開源模型（Llama, Qwen 等） |
| **隱私** | 資料傳送至 Google | 完全本地，無資料外傳 |
| **網路需求** | 需要網際網路 | 無需網際網路 |
| **硬體需求** | 無 | 建議 16GB+ RAM，GPU 更佳 |
| **設定難度** | 簡單（需 API 金鑰） | 中等（需安裝 Ollama） |

### 建議使用場景

- **Vertex AI**: 生產環境、需要最佳品質、雲端部署
- **Ollama**: 開發測試、隱私敏感、離線環境、降低成本

## 🧪 測試

執行安全性測試：

```bash
pytest tests/test_security.py -v
```

執行所有測試：

```bash
pytest tests/ -v
```

## 🔒 安全機制

### SQL 驗證規則

1. ✅ 必須以 `SELECT` 開頭
2. ❌ 禁止以下關鍵字：
   - `INSERT`, `UPDATE`, `DELETE`, `DROP`, `TRUNCATE`
   - `ALTER`, `CREATE`, `EXEC`, `EXECUTE`
   - `MERGE`, `GRANT`, `REVOKE`, `DENY`
   - `sp_executesql`, `xp_cmdshell`, `BACKUP`, `RESTORE`
3. ❌ 不允許多個 SQL 語句（分號）
4. ❌ 不允許 SQL 註解 (`--`, `/* */`)
5. ❌ 不允許 `SELECT INTO`

### 資料庫權限建議

在 SQL Server 中建立唯讀使用者：

```sql
-- 建立登入
CREATE LOGIN sql_agent_reader WITH PASSWORD = 'StrongPassword123!';

-- 建立使用者
USE YourDatabase;
CREATE USER sql_agent_reader FOR LOGIN sql_agent_reader;

-- 授予唯讀權限
ALTER ROLE db_datareader ADD MEMBER sql_agent_reader;

-- 移除其他權限（確保唯讀）
DENY INSERT, UPDATE, DELETE, EXECUTE ON SCHEMA::dbo TO sql_agent_reader;
```

## 📁 專案結構

```
SQL-Agent/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 應用程式主體
│   ├── vertex_client.py     # Vertex AI 整合
│   ├── db_handler.py        # SQL Server 連線
│   ├── security.py          # SQL 安全驗證
│   └── schema.py            # 資料庫結構定義
├── static/
│   ├── index.html           # 前端介面
│   ├── style.css            # 樣式表
│   └── script.js            # 前端邏輯
├── tests/
│   ├── __init__.py
│   └── test_security.py     # 安全性測試
├── openspec/                # OpenSpec 文件
│   ├── project.md           # 專案規範
│   └── AGENTS.md            # AI 開發指引
├── requirements.txt         # Python 相依套件
├── .env.example             # 環境變數範本
└── README.md                # 專案說明
```

## 🛠️ 開發指南

### 修改資料庫結構

編輯 `app/schema.py` 中的 `DEFAULT_SCHEMA` 常數。

### 調整安全規則

編輯 `app/security.py` 中的 `DANGEROUS_KEYWORDS` 列表或 `is_safe_sql()` 函式。

### 更換 LLM 模型

在 `.env` 中設定 `VERTEX_MODEL`：

- `gemini-pro` (預設，推薦)
- `gemini-1.5-flash` (更快)
- `text-bison@002` (PaLM 2)

### 客製化 Prompt

編輯 `app/vertex_client.py` 中的 `_build_prompt()` 方法。

## ⚠️ 注意事項

1. **生產環境部署**
   - 使用 HTTPS
   - 設定適當的 CORS 原則
   - 啟用身份驗證和授權
   - 監控 API 使用率

2. **成本控制**
   - Vertex AI 按請求計費
   - 建議設定請求頻率限制
   - 監控 GCP 用量

3. **資料隱私**
   - 資料庫 Schema 會傳送至 Vertex AI
   - 查詢結果資料不會傳送至 Vertex AI
   - 遵守組織的資料處理政策

## 🐛 疑難排解

### ODBC 驅動程式錯誤

安裝 Microsoft ODBC Driver：
- Windows: [下載連結](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
- Linux: `sudo apt-get install unixodbc-dev`

### Vertex AI 認證失敗

確認：
1. `GOOGLE_APPLICATION_CREDENTIALS` 路徑正確
2. 服務帳號有 Vertex AI 使用者權限
3. 專案已啟用 Vertex AI API

### 資料庫連線失敗

檢查：
1. SQL Server 允許遠端連線
2. 防火牆開放 1433 埠
3. 資料庫帳號密碼正確
4. SQL Server 啟用 TCP/IP 協定

## 📄 授權

本專案僅供內部使用。

## 🤝 貢獻

如有問題或建議，請聯繫開發團隊。

---

**版本**: 1.0.0
**最後更新**: 2024-10
**維護者**: 開發團隊
