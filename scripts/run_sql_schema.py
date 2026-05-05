import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


def load_config():
    """Load database configuration from .env file."""
    config_path = Path(__file__).parent.parent / "config" / ".env"
    load_dotenv(config_path)

    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5433hhhhhhh"),
        "database": os.getenv("DB_NAME", "arxiv_papers"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
    }


def run_sql_schema():
    """Run the SQL schema file against the PostgreSQL database."""

    # Path to schema.sql
    schema_path = Path(__file__).parent.parent / "sql" / "schema.sql"

    if not schema_path.exists():
        raise FileNotFoundError(f"schema.sql file not found at: {schema_path}")

    # Load database configuration
    db_config = load_config()

    # Read SQL schema file
    sql_script = schema_path.read_text(encoding="utf-8")

    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**db_config)

        with conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_script)

        print("schema.sql executed successfully.")

    except Exception as e:
        print("Error while executing schema.sql:")
        print(e)

    finally:
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    run_sql_schema()