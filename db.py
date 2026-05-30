import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_conn():
    print("DATABASE_URL =", os.getenv("DATABASE_URL"))
    return psycopg2.connect(
        os.getenv("DATABASE_URL"),
        cursor_factory=RealDictCursor
    )

TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
