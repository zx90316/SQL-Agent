"""
Database Handler Module
Manages SQL Server connections and query execution.
"""

import os
import pyodbc
import logging
from typing import List, Tuple, Optional, Any
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseHandler:
    """Handles SQL Server database connections and query execution."""

    def __init__(
        self,
        server: str,
        database: str,
        username: str,
        password: str,
        driver: str = "ODBC Driver 17 for SQL Server"
    ):
        """
        Initialize database handler.

        Args:
            server: SQL Server hostname or IP
            database: Database name
            username: Database username (should have read-only access)
            password: Database password
            driver: ODBC driver name
        """
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.driver = driver

        self.connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"TrustServerCertificate=yes;"
        )

        logger.info(f"Database handler initialized for {server}/{database}")

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Yields:
            pyodbc.Connection: Database connection

        Raises:
            Exception: If connection fails
        """
        conn = None
        try:
            conn = pyodbc.connect(self.connection_string, timeout=10)
            logger.info("Database connection established")
            yield conn
        except pyodbc.Error as e:
            logger.error(f"Database connection error: {e}")
            raise Exception(f"Failed to connect to database: {str(e)}")
        finally:
            if conn:
                conn.close()
                logger.info("Database connection closed")

    async def execute_query(self, sql_query: str) -> Tuple[List[str], List[List[Any]]]:
        """
        Execute a SQL query and return results.

        Args:
            sql_query: SQL SELECT query to execute

        Returns:
            Tuple containing:
                - List[str]: Column names
                - List[List[Any]]: Rows of data

        Raises:
            Exception: If query execution fails
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                logger.info(f"Executing query: {sql_query[:100]}...")

                # Execute the query
                cursor.execute(sql_query)

                # Get column names
                columns = [column[0] for column in cursor.description]

                # Fetch all rows
                rows = cursor.fetchall()

                # Convert rows to list of lists for JSON serialization
                data = []
                for row in rows:
                    # Convert Row object to list, handling None and special types
                    row_data = []
                    for value in row:
                        if value is None:
                            row_data.append(None)
                        elif isinstance(value, (int, float, str, bool)):
                            row_data.append(value)
                        else:
                            # Convert other types (datetime, decimal, etc.) to string
                            row_data.append(str(value))
                    data.append(row_data)

                logger.info(f"Query returned {len(data)} rows with {len(columns)} columns")

                return columns, data

        except pyodbc.Error as e:
            logger.error(f"Query execution error: {e}")
            raise Exception(f"Failed to execute query: {str(e)}")

    async def test_connection(self) -> bool:
        """
        Test database connectivity.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                logger.info("Database connection test successful")
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    async def get_database_info(self) -> dict:
        """
        Get basic database information.

        Returns:
            dict: Database metadata
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get SQL Server version
                cursor.execute("SELECT @@VERSION")
                version = cursor.fetchone()[0]

                # Get database name
                cursor.execute("SELECT DB_NAME()")
                db_name = cursor.fetchone()[0]

                return {
                    "database": db_name,
                    "server": self.server,
                    "version": version.split('\n')[0] if version else "Unknown"
                }
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {}


# Singleton instance
_db_handler: Optional[DatabaseHandler] = None


def get_db_handler() -> DatabaseHandler:
    """
    Get or create singleton database handler instance.

    Returns:
        DatabaseHandler: Initialized database handler

    Raises:
        ValueError: If required environment variables are missing
    """
    global _db_handler

    if _db_handler is None:
        server = os.getenv("DB_SERVER")
        database = os.getenv("DB_NAME")
        username = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        driver = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")

        if not all([server, database, username, password]):
            raise ValueError(
                "Database environment variables are required: "
                "DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD"
            )

        _db_handler = DatabaseHandler(
            server=server,
            database=database,
            username=username,
            password=password,
            driver=driver
        )

    return _db_handler
