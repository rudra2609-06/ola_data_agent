import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timezone

from psycopg2 import sql
from sqlmodel import Session, select
from utils.db_connection import engine
from models.schema import ContextTbl

from utils.db import DatabaseUtil

logger = logging.getLogger(__name__)


def cleanup_expired_table():
    db_obj = DatabaseUtil(
        {
            "host": "localhost",
            "port": 5432,
            "dbname": "postgres",
            "user": "postgres",
            "password": os.getenv("POSTGRES_PASSWORD"),
        }
    )
    conn = db_obj.connection

    try:
        with Session(engine) as session:
            expired = session.exec(
                select(ContextTbl).where(
                    ContextTbl.expires_at < datetime.now(timezone.utc)
                )
            ).all()
            for row in expired:
                try:
                    if not row.table_name.startswith("user_"):
                        continue
                    with db_obj.connection.cursor() as cursor:
                        cursor.execute(
                            sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
                                sql.Identifier("public"), sql.Identifier(row.table_name)
                            )
                        )
                    conn.commit()
                    session.delete(row)
                    logger.info("Deleted Expired Table: %s", row.table_name)

                except Exception as e:
                    conn.rollback()
                    session.rollback()
                    logger.exception(f"Failed Deleting the Table.Reason: {e}")

    finally:
        if conn:
            conn.close()
