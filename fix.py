import os
import psycopg2
from psycopg2 import sql


def connect_db():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise Exception("❌ DATABASE_URL environment variable is not set.")
    conn = psycopg2.connect(db_url)
    return conn


def check_column_exists(conn, table, column):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s;
        """, (table, column))
        return cur.fetchone() is not None


def drop_invalid_column(conn, table, column):
    with conn.cursor() as cur:
        print(f"🔍 Checking if '{column}' exists in '{table}'...")
        if check_column_exists(conn, table, column):
            cur.execute(
                sql.SQL("ALTER TABLE {} DROP COLUMN {};").format(
                    sql.Identifier(table), sql.Identifier(column)))
            conn.commit()
            print(f"✅ Column '{column}' dropped from '{table}'.")
        else:
            print(f"✔️ Column '{column}' does not exist. No action taken.")


def print_current_db(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT current_database();")
        current_db = cur.fetchone()[0]
        print(f"📌 Connected to database: {current_db}")


if __name__ == "__main__":
    try:
        conn = connect_db()
        print_current_db(conn)
        drop_invalid_column(conn, "tutor", "user_id")
    except Exception as e:
        print("❌ Error:", e)
    finally:
        if conn:
            conn.close()
