"""
Security Module Tests
Tests for SQL validation and sanitization functions.
"""

import pytest
from app.security import is_safe_sql, sanitize_sql_response, validate_query_result_size, remove_sql_comments


class TestIsSafeSQL:
    """Test cases for SQL safety validation."""

    def test_valid_select_query(self):
        """Test that valid SELECT queries pass validation."""
        queries = [
            "SELECT * FROM Users",
            "SELECT TOP 10 * FROM Orders WHERE Status = 'Pending'",
            "SELECT u.Username, o.OrderID FROM Users u JOIN Orders o ON u.UserID = o.UserID",
            "SELECT COUNT(*) FROM Products WHERE Price > 100",
            "SELECT * FROM LoginLogs WHERE LoginTime > DATEADD(day, -7, GETDATE())",
        ]

        for query in queries:
            is_safe, error = is_safe_sql(query)
            assert is_safe, f"Valid query rejected: {query}, Error: {error}"
            assert error == "", f"Error message should be empty for valid query"

    def test_dangerous_keywords_rejected(self):
        """Test that queries with dangerous keywords are rejected."""
        dangerous_queries = [
            "INSERT INTO Users VALUES (1, 'test')",
            "UPDATE Users SET Username = 'hacked' WHERE UserID = 1",
            "DELETE FROM Orders WHERE OrderID = 1",
            "DROP TABLE Users",
            "TRUNCATE TABLE LoginLogs",
            "ALTER TABLE Users ADD COLUMN Evil VARCHAR(50)",
            "CREATE TABLE Malicious (id INT)",
            "EXEC sp_executesql 'SELECT * FROM Users'",
            "EXECUTE xp_cmdshell 'dir'",
            "MERGE INTO Users AS target",
            "GRANT SELECT ON Users TO public",
            "REVOKE SELECT ON Users FROM user1",
            "SELECT * FROM Users; DROP TABLE Users;",
        ]

        for query in dangerous_queries:
            is_safe, error = is_safe_sql(query)
            assert not is_safe, f"Dangerous query not rejected: {query}"
            assert error != "", f"Error message should be provided for dangerous query"

    def test_non_select_queries_rejected(self):
        """Test that queries not starting with SELECT are rejected."""
        invalid_queries = [
            "SHOW TABLES",
            "DESCRIBE Users",
            "CALL stored_procedure()",
            "",  # Empty query
            "   ",  # Whitespace only
        ]

        for query in invalid_queries:
            is_safe, error = is_safe_sql(query)
            assert not is_safe, f"Non-SELECT query not rejected: {query}"

    def test_multiple_statements_rejected(self):
        """Test that multiple statements are rejected."""
        queries = [
            "SELECT * FROM Users; SELECT * FROM Orders",
            "SELECT * FROM Users; -- comment",
            "SELECT UserID FROM Users WHERE UserID = 1; UPDATE Users SET Username = 'test'",
        ]

        for query in queries:
            is_safe, error = is_safe_sql(query)
            assert not is_safe, f"Multiple statements not rejected: {query}"

    def test_sql_comments_rejected(self):
        """Test that SQL comments are rejected (after sanitization, they should be removed)."""
        # After sanitization, comments should be removed, so these will pass validation
        # The sanitize_sql_response function handles comment removal
        queries_with_comments = [
            "SELECT * FROM Users -- this is a comment",
            "SELECT * FROM Users /* block comment */",
            "SELECT * FROM Users WHERE Username = 'admin' --",
        ]

        # These queries still contain comments and should be rejected if not sanitized
        for query in queries_with_comments:
            is_safe, error = is_safe_sql(query)
            assert not is_safe, f"Query with comments not rejected: {query}"

    def test_select_into_rejected(self):
        """Test that SELECT INTO is rejected."""
        queries = [
            "SELECT * INTO NewTable FROM Users",
            "SELECT UserID, Username INTO #TempTable FROM Users",
        ]

        for query in queries:
            is_safe, error = is_safe_sql(query)
            assert not is_safe, f"SELECT INTO not rejected: {query}"

    def test_case_insensitivity(self):
        """Test that validation is case-insensitive."""
        queries = [
            "select * from Users",
            "SeLeCt * FrOm Users",
            "SELECT * FROM Users",
        ]

        for query in queries:
            is_safe, error = is_safe_sql(query)
            assert is_safe, f"Case variation rejected incorrectly: {query}"

        dangerous_queries = [
            "select * from Users; drop table Users",
            "SELECT * FROM Users; DELETE FROM Orders",
        ]

        for query in dangerous_queries:
            is_safe, error = is_safe_sql(query)
            assert not is_safe, f"Dangerous query with case variation not rejected: {query}"

    def test_trailing_semicolon_allowed(self):
        """Test that trailing semicolon is allowed."""
        queries = [
            "SELECT * FROM Users;",
            "SELECT * FROM Users WHERE UserID = 1;",
        ]

        for query in queries:
            is_safe, error = is_safe_sql(query)
            assert is_safe, f"Query with trailing semicolon rejected: {query}"


class TestSanitizeSQLResponse:
    """Test cases for SQL response sanitization."""

    def test_clean_sql_unchanged(self):
        """Test that clean SQL is unchanged."""
        sql = "SELECT * FROM Users"
        result = sanitize_sql_response(sql)
        assert result == sql

    def test_markdown_code_blocks_removed(self):
        """Test that markdown code blocks are removed."""
        inputs_and_expected = [
            ("```sql\nSELECT * FROM Users\n```", "SELECT * FROM Users"),
            ("```\nSELECT * FROM Users\n```", "SELECT * FROM Users"),
            ("```sql\nSELECT * FROM Users", "SELECT * FROM Users"),
            ("SELECT * FROM Users\n```", "SELECT * FROM Users"),
        ]

        for input_sql, expected in inputs_and_expected:
            result = sanitize_sql_response(input_sql)
            assert result == expected, f"Failed to sanitize: {input_sql}"

    def test_whitespace_trimmed(self):
        """Test that leading/trailing whitespace is removed."""
        inputs = [
            "   SELECT * FROM Users   ",
            "\n\nSELECT * FROM Users\n\n",
            "\t\tSELECT * FROM Users\t\t",
        ]

        for input_sql in inputs:
            result = sanitize_sql_response(input_sql)
            assert result == "SELECT * FROM Users"

    def test_extract_select_from_multiline(self):
        """Test extraction of SELECT from multiline text."""
        input_text = """
        Here is the SQL query you requested:

        SELECT * FROM Users WHERE UserID = 1

        This query will return the user with ID 1.
        """

        result = sanitize_sql_response(input_text)
        assert result.startswith("SELECT"), "Should extract SELECT statement"
        assert "Users" in result, "Should contain table name"

    def test_remove_comments_from_sql(self):
        """Test that SQL comments are removed during sanitization."""
        inputs_and_expected = [
            (
                "SELECT * FROM Users -- get all users",
                "SELECT * FROM Users"
            ),
            (
                "SELECT * FROM Users /* get all users */ WHERE Active = 1",
                "SELECT * FROM Users  WHERE Active = 1"
            ),
            (
                """SELECT
                    UserID, -- user identifier
                    Username -- user name
                FROM Users""",
                "SELECT\n    UserID,\n    Username\nFROM Users"
            ),
        ]

        for input_sql, expected in inputs_and_expected:
            result = sanitize_sql_response(input_sql)
            # Normalize whitespace for comparison
            assert result.replace(" ", "").replace("\n", "") == expected.replace(" ", "").replace("\n", ""), \
                f"Failed to remove comments from: {input_sql}"


class TestRemoveSQLComments:
    """Test cases for SQL comment removal."""

    def test_remove_single_line_comments(self):
        """Test removal of single-line comments."""
        sql = "SELECT * FROM Users -- this is a comment"
        result = remove_sql_comments(sql)
        assert "--" not in result
        assert "SELECT * FROM Users" in result

    def test_remove_block_comments(self):
        """Test removal of block comments."""
        sql = "SELECT * FROM Users /* this is a comment */ WHERE Active = 1"
        result = remove_sql_comments(sql)
        assert "/*" not in result
        assert "*/" not in result
        assert "SELECT" in result
        assert "WHERE Active = 1" in result

    def test_remove_multiline_block_comments(self):
        """Test removal of multi-line block comments."""
        sql = """SELECT * FROM Users
        /* this is a
           multi-line comment */
        WHERE Active = 1"""
        result = remove_sql_comments(sql)
        assert "/*" not in result
        assert "WHERE Active = 1" in result


class TestValidateQueryResultSize:
    """Test cases for query result size validation."""

    def test_within_limit(self):
        """Test that results within limit pass validation."""
        is_valid, message = validate_query_result_size(100, max_rows=1000)
        assert is_valid
        assert message == ""

    def test_at_limit(self):
        """Test that results at exactly the limit pass validation."""
        is_valid, message = validate_query_result_size(1000, max_rows=1000)
        assert is_valid
        assert message == ""

    def test_exceeds_limit(self):
        """Test that results exceeding limit fail validation."""
        is_valid, message = validate_query_result_size(1001, max_rows=1000)
        assert not is_valid
        assert "1001" in message
        assert "1000" in message

    def test_custom_limit(self):
        """Test validation with custom limit."""
        is_valid, message = validate_query_result_size(51, max_rows=50)
        assert not is_valid
        assert "51" in message
        assert "50" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
