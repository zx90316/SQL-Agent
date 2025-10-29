# Project Context

## Purpose
Internal web application that allows users to query SQL Server databases using natural language. The system uses Google Cloud Vertex AI to generate SQL queries from user input, with strict security controls to ensure read-only access and data privacy.

**Critical Privacy Requirement**: Database data NEVER sent to Vertex AI. LLM only receives schema information and generates SQL syntax strings.

## Tech Stack
- **Backend**: FastAPI (Python 3.11)
- **Frontend**: HTML, CSS, JavaScript (minimal, vanilla JS for API calls)
- **LLM Service**: Google Cloud Vertex AI (PaLM 2 / Gemini models)
- **Database**: Microsoft SQL Server
- **Database Driver**: pyodbc or sqlalchemy
- **Cloud SDK**: google-cloud-aiplatform

## Project Conventions

### Code Style
- **Language**: Python 3.11+ for backend
- **Async/Await**: Use async patterns for I/O operations
- **Type Hints**: Use Pydantic models for API request/response
- **Error Handling**: Explicit try-catch with HTTPException for API errors
- **Security First**: All SQL queries MUST pass validation before execution

### Architecture Patterns
- **Modular Design**: Separate concerns into distinct modules:
  - `main.py`: FastAPI endpoints
  - `vertex_client.py`: LLM communication
  - `db_handler.py`: Database operations
  - `security.py`: SQL validation logic
  - `schema.py`: Database schema definitions
- **Security Layer**: Mandatory SQL validation between LLM generation and execution
- **Read-Only Database Access**: Use db_datareader permissions only
- **Static File Serving**: Frontend served via FastAPI's StaticFiles

### Testing Strategy
- **SQL Security Tests**: Validate all dangerous keywords are blocked
- **LLM Response Parsing**: Test extraction of SQL from various LLM response formats
- **Database Integration**: Test queries against sample schema
- **Frontend Integration**: Verify end-to-end flow from natural language to results

### Git Workflow
- Standard feature branch workflow
- Clear commit messages describing changes
- Review before merge

## Domain Context
- **SQL Server T-SQL Syntax**: Generated queries must be valid T-SQL
- **Natural Language Processing**: Support Chinese (zh-Hant) and English queries
- **Schema-Aware Generation**: LLM needs complete table/column structure to generate accurate queries
- **Read-Only Operations**: Only SELECT statements allowed
- **Database Security**: Never expose credentials; use environment variables

## Important Constraints
- **Security**: Absolutely no UPDATE, DELETE, INSERT, DROP, TRUNCATE, ALTER, CREATE, EXEC, EXECUTE, MERGE, GRANT, REVOKE, sp_executesql
- **Privacy**: Database result data must never be sent to Vertex AI
- **SQL Validation**: Multi-layer validation:
  1. Must start with SELECT
  2. Blacklist dangerous keywords (regex word boundary matching)
  3. Prevent multiple statements (no semicolons except at end)
- **Database Permissions**: Query execution account must have ONLY db_datareader role
- **Performance**: Single query at a time (no batch operations)

## External Dependencies
- **Google Cloud Vertex AI**: Requires service account credentials (JSON key file)
- **SQL Server**: Connection string required (host, database, user, password)
- **Environment Variables**: Store in `.env` file:
  - Database connection string
  - GCP credentials path
  - Vertex AI project ID and location
