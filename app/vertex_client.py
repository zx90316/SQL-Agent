"""
LLM Client Module
Handles communication with LLM providers (Vertex AI or Ollama) for SQL generation from natural language.
"""

import os
import logging
from typing import Optional, Protocol

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    """Protocol for LLM clients."""

    async def generate_sql_from_nl(self, nl_query: str, schema_info: str) -> str:
        """Generate SQL from natural language."""
        ...

    def _build_prompt(self, nl_query: str, schema_info: str) -> str:
        """Build prompt for LLM."""
        ...


class VertexAIClient:
    """Client for interacting with Google Cloud Vertex AI using official genai SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.0-flash-exp"
    ):
        """
        Initialize Vertex AI client.

        Args:
            api_key: Google Cloud API key (optional, uses GOOGLE_CLOUD_API_KEY env var if not provided)
            model_name: Model to use (default: gemini-2.0-flash-exp)
        """
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("GOOGLE_CLOUD_API_KEY")

        # Initialize genai Client
        try:
            from google import genai
            self.client = genai.Client(
                vertexai=True,
                api_key=self.api_key
            )
            logger.info(f"Vertex AI client initialized: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI client: {e}")
            raise

    async def generate_sql_from_nl(
        self,
        nl_query: str,
        schema_info: str
    ) -> str:
        """
        Generate SQL query from natural language using Vertex AI.

        Args:
            nl_query: Natural language query from user
            schema_info: Database schema information

        Returns:
            str: Generated SQL query

        Raises:
            Exception: If LLM generation fails
        """
        try:
            from google.genai import types

            # Construct the prompt
            prompt = self._build_prompt(nl_query, schema_info)

            logger.info(f"Sending request to Vertex AI for query: {nl_query[:50]}...")

            # Build content
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part(text=prompt)]
                )
            ]

            # Configure generation
            generate_content_config = types.GenerateContentConfig(
                temperature=0.1,  # Low temperature for consistent SQL generation
                top_p=0.95,
                max_output_tokens=10000,
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold="OFF"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="OFF"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold="OFF"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="OFF"
                    )
                ],
                thinking_config=types.ThinkingConfig(
                thinking_budget=-1,
                ),
            )

            # Generate response (streaming)
            sql_query = ""
            for chunk in self.client.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=generate_content_config
            ):
                if hasattr(chunk, 'text') and chunk.text:
                    sql_query += chunk.text

            sql_query = sql_query.strip()
            logger.info(f"Received SQL from Vertex AI: {sql_query[:100]}...")

            return sql_query

        except Exception as e:
            logger.error(f"Error generating SQL from Vertex AI: {e}")
            raise Exception(f"Vertex AI generation failed: {str(e)}")

    def _build_prompt(self, nl_query: str, schema_info: str) -> str:
        """
        Build the prompt for Vertex AI.

        Args:
            nl_query: Natural language query
            schema_info: Database schema

        Returns:
            str: Complete prompt for LLM
        """
        prompt = f"""你是一個 SQL Server T-SQL 專家。你的任務是將使用者的自然語言請求轉換為安全的 SQL 查詢。

資料庫結構 (Database Schema)：
{schema_info}

重要規則：
1. 只能生成 SELECT 查詢（絕對不可使用 UPDATE, DELETE, INSERT, DROP, EXEC 等）
2. 必須使用 T-SQL (SQL Server) 語法
3. 只回傳純 SQL 查詢語法，絕對不要包含任何註解（不可使用 -- 或 /* */ 註解）
4. 不要有任何額外的說明文字、markdown 標記或程式碼區塊符號
5. 確保查詢語法完整且正確
6. 如果需要限制筆數，使用 TOP 子句
7. 使用適當的 WHERE 條件和 JOIN 來過濾資料
8. 對於日期查詢，使用 GETDATE() 或 DATEADD() 等函數
9. 對於中文搜尋，使用 LIKE N'%關鍵字%' 語法
10. 確保 SQL 語法完整，不要截斷或省略任何部分

使用者的自然語言請求：
{nl_query}

請生成對應的 T-SQL SELECT 查詢語法（純 SQL，無註解）：
"""
        return prompt


class OllamaClient:
    """Client for interacting with local Ollama instance."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "llama3.1:8b"
    ):
        """
        Initialize Ollama client.

        Args:
            base_url: Ollama API base URL (default: http://localhost:11434)
            model_name: Model to use (default: llama3.1:8b)
        """
        self.base_url = base_url
        self.model_name = model_name

        try:
            import ollama
            self.client = ollama.Client(host=base_url)
            logger.info(f"Ollama client initialized: {model_name} at {base_url}")
        except ImportError:
            raise ImportError(
                "ollama package is required for Ollama support. "
                "Install it with: pip install ollama"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {e}")
            raise

    async def generate_sql_from_nl(
        self,
        nl_query: str,
        schema_info: str
    ) -> str:
        """
        Generate SQL query from natural language using Ollama.

        Args:
            nl_query: Natural language query from user
            schema_info: Database schema information

        Returns:
            str: Generated SQL query

        Raises:
            Exception: If LLM generation fails
        """
        try:
            # Construct the prompt
            prompt = self._build_prompt(nl_query, schema_info)

            logger.info(f"Sending request to Ollama for query: {nl_query[:50]}...")

            # Generate response (streaming)
            sql_query = ""
            stream = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                stream=True,
                options={
                    "temperature": 0.1,  # Low temperature for consistent SQL generation
                    "top_p": 0.95,
                    "num_predict": 2048,
                }
            )

            for chunk in stream:
                if 'response' in chunk:
                    sql_query += chunk['response']

            sql_query = sql_query.strip()
            logger.info(f"Received SQL from Ollama: {sql_query[:100]}...")

            return sql_query

        except Exception as e:
            logger.error(f"Error generating SQL from Ollama: {e}")
            raise Exception(f"Ollama generation failed: {str(e)}")

    def _build_prompt(self, nl_query: str, schema_info: str) -> str:
        """
        Build the prompt for Ollama.

        Args:
            nl_query: Natural language query
            schema_info: Database schema

        Returns:
            str: Complete prompt for LLM
        """
        prompt = f"""你是一個 SQL Server T-SQL 專家。你的任務是將使用者的自然語言請求轉換為安全的 SQL 查詢。

資料庫結構 (Database Schema)：
{schema_info}

重要規則：
1. 只能生成 SELECT 查詢（絕對不可使用 UPDATE, DELETE, INSERT, DROP, EXEC 等）
2. 必須使用 T-SQL (SQL Server) 語法
3. 只回傳純 SQL 查詢語法，絕對不要包含任何註解（不可使用 -- 或 /* */ 註解）
4. 不要有任何額外的說明文字、markdown 標記或程式碼區塊符號
5. 確保查詢語法完整且正確
6. 如果需要限制筆數，使用 TOP 子句而不是 LIMIT
7. 使用適當的 WHERE 條件和 JOIN 來過濾資料
8. 對於日期查詢，使用 GETDATE() 或 DATEADD() 等函數
9. 對於中文搜尋，使用 LIKE N'%關鍵字%' 語法
10. 確保 SQL 語法完整，不要截斷或省略任何部分

使用者的自然語言請求：
{nl_query}

請生成對應的 T-SQL SELECT 查詢語法（純 SQL，無註解）：
"""
        return prompt


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_vertex_client() -> LLMClient:
    """
    Get or create singleton LLM client instance based on LLM_PROVIDER env var.

    Returns:
        LLMClient: Initialized client (VertexAI or Ollama)

    Raises:
        ValueError: If required environment variables are missing
    """
    global _llm_client

    if _llm_client is None:
        provider = os.getenv("LLM_PROVIDER", "vertexai").lower()

        if provider == "vertexai":
            from google import genai
            from google.genai import types

            api_key = os.getenv("GOOGLE_CLOUD_API_KEY")
            model_name = os.getenv("VERTEX_MODEL", "gemini-2.5-flash")

            if not api_key:
                raise ValueError("GOOGLE_CLOUD_API_KEY environment variable is required for Vertex AI")

            _llm_client = VertexAIClient(
                api_key=api_key,
                model_name=model_name
            )
            logger.info("Using Vertex AI as LLM provider")

        elif provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            model_name = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

            _llm_client = OllamaClient(
                base_url=base_url,
                model_name=model_name
            )
            logger.info("Using Ollama as LLM provider")

        else:
            raise ValueError(
                f"Invalid LLM_PROVIDER: {provider}. "
                "Must be 'vertexai' or 'ollama'"
            )

    return _llm_client
