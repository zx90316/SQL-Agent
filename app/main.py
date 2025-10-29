"""
FastAPI Application - SQL Server Natural Language Query Tool
Main application entry point with API endpoints.
"""

import os
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Any, Optional
from dotenv import load_dotenv

from app import schema, security, vertex_client, db_handler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SQL Server Natural Language Query Tool",
    description="Query SQL Server databases using natural language powered by Vertex AI",
    version="1.0.0"
)

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class QueryRequest(BaseModel):
    """Request model for natural language query."""
    nl_query: str = Field(..., min_length=1, description="Natural language query in Chinese or English")


class QueryResponse(BaseModel):
    """Response model for query results."""
    query_generated: str = Field(..., description="Generated SQL query")
    columns: List[str] = Field(..., description="Column names")
    data: List[List[Any]] = Field(..., description="Query result rows")
    row_count: int = Field(..., description="Number of rows returned")


class ErrorResponse(BaseModel):
    """Response model for errors."""
    detail: str = Field(..., description="Error message")
    error_type: Optional[str] = Field(None, description="Type of error")


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    try:
        logger.info("Starting SQL-Agent application...")

        # Test database connection
        db = db_handler.get_db_handler()
        is_connected = await db.test_connection()

        if not is_connected:
            logger.warning("Database connection test failed on startup")
        else:
            db_info = await db.get_database_info()
            logger.info(f"Connected to database: {db_info.get('database', 'Unknown')}")

        # Initialize Vertex AI client
        vertex_ai = vertex_client.get_vertex_client()
        logger.info("Vertex AI client initialized")

        logger.info("Application startup complete")

    except Exception as e:
        logger.error(f"Startup error: {e}")


# API Endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect to static frontend."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="0; url=/static/index.html">
    </head>
    <body>
        <p>Redirecting to <a href="/static/index.html">application</a>...</p>
    </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        db = db_handler.get_db_handler()
        db_connected = await db.test_connection()

        return {
            "status": "healthy" if db_connected else "degraded",
            "database": "connected" if db_connected else "disconnected",
            "vertex_ai": "initialized"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.post("/api/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    """
    Process natural language query and return SQL results.

    Workflow:
    1. Receive natural language query
    2. Get database schema
    3. Generate SQL using Vertex AI
    4. Validate SQL for security
    5. Execute SQL query
    6. Return results

    Args:
        request: QueryRequest containing natural language query

    Returns:
        QueryResponse with generated SQL and results

    Raises:
        HTTPException: For validation or execution errors
    """
    try:
        logger.info(f"Received query request: {request.nl_query[:100]}...")

        # Step 1: Get database schema
        db_schema = schema.get_db_schema()

        # Step 2: Generate SQL using Vertex AI
        try:
            vertex_ai = vertex_client.get_vertex_client()
            raw_sql = await vertex_ai.generate_sql_from_nl(
                nl_query=request.nl_query,
                schema_info=db_schema
            )
            logger.info(f"Raw SQL from Vertex AI: {raw_sql}")
        except Exception as e:
            logger.error(f"Vertex AI error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate SQL: {str(e)}"
            )

        # Step 3: Clean and sanitize SQL response
        sql_query = security.sanitize_sql_response(raw_sql)
        logger.info(f"Sanitized SQL: {sql_query}")

        # Step 4: Validate SQL for security
        is_safe, error_message = security.is_safe_sql(sql_query)
        if not is_safe:
            logger.warning(f"Unsafe SQL detected: {error_message}")
            raise HTTPException(
                status_code=400,
                detail=f"Generated SQL is not safe: {error_message}"
            )

        logger.info("SQL passed security validation")

        # Step 5: Execute SQL query
        try:
            db = db_handler.get_db_handler()
            columns, rows = await db.execute_query(sql_query)
        except Exception as e:
            logger.error(f"Database execution error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to execute query: {str(e)}"
            )

        # Step 6: Validate result size
        row_count = len(rows)
        is_valid_size, warning = security.validate_query_result_size(row_count)
        if not is_valid_size:
            logger.warning(warning)
            raise HTTPException(
                status_code=400,
                detail=warning
            )

        logger.info(f"Query successful: {row_count} rows returned")

        # Return results
        return QueryResponse(
            query_generated=sql_query,
            columns=columns,
            data=rows,
            row_count=row_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/api/schema")
async def get_schema_info():
    """Get database schema information."""
    try:
        return {
            "schema": schema.get_db_schema(),
            "tables": schema.get_table_list()
        }
    except Exception as e:
        logger.error(f"Failed to get schema: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve schema: {str(e)}"
        )


@app.get("/api/tables")
async def get_tables():
    """Get list of available tables."""
    try:
        tables = schema.get_table_list()
        return {"tables": tables}
    except Exception as e:
        logger.error(f"Failed to get tables: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve tables: {str(e)}"
        )


# Mount static files (must be last)
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", 8000))

    logger.info(f"Starting server on {host}:{port}")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
