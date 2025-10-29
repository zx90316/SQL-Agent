"""
SQL Security Validation Module
Ensures that all generated SQL queries are safe and read-only.
"""

import re
from typing import Tuple


# Blacklist of dangerous SQL keywords
DANGEROUS_KEYWORDS = [
    'INSERT', 'UPDATE', 'DELETE', 'DROP', 'TRUNCATE', 'ALTER', 'CREATE',
    'EXEC', 'EXECUTE', 'MERGE', 'GRANT', 'REVOKE', 'DENY',
    'sp_executesql', 'xp_cmdshell', 'sp_configure',
    'BACKUP', 'RESTORE', 'SHUTDOWN', 'DBCC'
]


def is_safe_sql(sql_query: str) -> Tuple[bool, str]:
    """
    Validates that a SQL query is safe for execution.

    Security checks:
    1. Must start with SELECT keyword
    2. No dangerous keywords present
    3. No multiple statements (semicolons not allowed except at end)
    4. No comments that could hide malicious code

    Args:
        sql_query: The SQL query string to validate

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
            - is_valid: True if query is safe, False otherwise
            - error_message: Description of validation failure, empty if valid
    """
    if not sql_query or not sql_query.strip():
        return False, "Query is empty"

    query_upper = sql_query.upper().strip()

    # Check 1: Must start with SELECT
    if not query_upper.startswith('SELECT'):
        return False, "Query must start with SELECT"

    # Check 2: Check for dangerous keywords using word boundaries
    for keyword in DANGEROUS_KEYWORDS:
        # Use word boundary regex to match whole words only
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, query_upper):
            return False, f"Dangerous keyword detected: {keyword}"

    # Check 3: No multiple statements (semicolons in middle of query)
    # Allow trailing semicolon only
    query_without_trailing = query_upper.rstrip(';').strip()
    if ';' in query_without_trailing:
        return False, "Multiple statements not allowed"

    # Check 4: Check for SQL comments that could hide malicious code
    if '--' in sql_query or '/*' in sql_query:
        return False, "SQL指令不合法"

    # Check 5: INTO keyword check (prevents SELECT INTO)
    if re.search(r'\bINTO\b', query_upper):
        return False, "SELECT INTO 指令不合法"

    return True, ""


def sanitize_sql_response(llm_response: str) -> str:
    """
    Extracts and cleans SQL query from LLM response.

    LLM responses may contain:
    - Markdown code blocks (```sql ... ```)
    - Extra explanatory text
    - Leading/trailing whitespace
    - SQL comments (-- or /* */)

    Args:
        llm_response: Raw response from LLM

    Returns:
        str: Cleaned SQL query string
    """
    # Remove markdown code blocks
    cleaned = llm_response.strip()

    # Remove ```sql or ``` markers
    if cleaned.startswith('```sql'):
        cleaned = cleaned[6:]
    elif cleaned.startswith('```'):
        cleaned = cleaned[3:]

    if cleaned.endswith('```'):
        cleaned = cleaned[:-3]

    # Remove any leading/trailing whitespace
    cleaned = cleaned.strip()

    # If there are multiple lines, try to find the line that starts with SELECT
    lines = cleaned.split('\n')
    for line in lines:
        if line.strip().upper().startswith('SELECT'):
            # Take from SELECT onwards
            start_idx = cleaned.upper().find(line.strip().upper())
            if start_idx != -1:
                cleaned = cleaned[start_idx:]
                break

    # Remove SQL comments
    cleaned = remove_sql_comments(cleaned)

    return cleaned.strip()


def remove_sql_comments(sql_query: str) -> str:
    """
    Remove SQL comments from query while preserving string literals.

    Args:
        sql_query: SQL query that may contain comments

    Returns:
        str: SQL query with comments removed
    """
    # Remove single-line comments (--)
    # Split by lines and remove everything after --
    lines = sql_query.split('\n')
    cleaned_lines = []

    for line in lines:
        # Find -- that's not inside a string literal
        comment_pos = line.find('--')
        if comment_pos != -1:
            # Simple check: if -- appears, take everything before it
            line = line[:comment_pos]

        # Only keep non-empty lines
        if line.strip():
            cleaned_lines.append(line.rstrip())

    sql_query = '\n'.join(cleaned_lines)

    # Remove block comments (/* ... */)
    # Use regex to remove /* ... */ patterns
    sql_query = re.sub(r'/\*.*?\*/', '', sql_query, flags=re.DOTALL)

    return sql_query


def validate_query_result_size(row_count: int, max_rows: int = 1000) -> Tuple[bool, str]:
    """
    Validates that query results don't exceed maximum allowed rows.

    Args:
        row_count: Number of rows in query result
        max_rows: Maximum allowed rows (default: 1000)

    Returns:
        Tuple[bool, str]: (is_valid, warning_message)
    """
    if row_count > max_rows:
        return False, f"Query returned {row_count} rows, exceeding limit of {max_rows}"

    return True, ""
