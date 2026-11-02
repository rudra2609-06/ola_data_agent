import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import UploadFile, File, HTTPException, status, Depends
from fastapi.routing import APIRouter
from fastapi.responses import JSONResponse
from uuid import uuid4
from psycopg2 import sql
from sqlmodel import Session
from datetime import datetime, timezone

from utils.db import DatabaseUtil
from models.schema import ContextTbl, AskRequest
from utils.db_connection import yeild_session
from agents.sql_analyst_agent import sql_analyst

from io import StringIO
import logging
import pandas as pd
import numpy as np

sql_router = APIRouter(prefix="/sql-analyst", tags=["sql-analyst"])

_logger = logging.getLogger(__name__)


# router for csv upload
@sql_router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_csv_file(
    file: UploadFile = File(
        description="Accepts CSV files in order to futher process in sql analyst agent",
        examples=["data.csv", "users.csv", "rides_details.csv"],
    ),
    session: Session = Depends(yeild_session),
):
    upload_id = uuid4()
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files is supported for processing with SQL Analyst Agent",
        )
    CHUNK = 1024 * 1024
    MAX_SIZE = CHUNK * 10
    total = 0
    chunks = []
    while chunk := await file.read(CHUNK):
        total += len(chunk)
        if total > MAX_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Max Size of CSV file should not exceed the limit of 10 MB",
            )
        chunks.append(chunk)

    content = b"".join(chunks)
    db_obj = DatabaseUtil(
        # {
        #     "host": os.environ.get("POSTGRES_DB_URL"),
        #     "port": 5432,
        #     "dbname": "postgres",
        #     "user": "postgres",
        #     "password": os.getenv("POSTGRES_PASSWORD"),
        # }
    )
    cursor = db_obj.connection.cursor()

    try:
        # parse the raw bytes into utf-8 by removing "byte order marks"
        parsed_content = content.decode("utf-8-sig")
        # convert into pd Dataframe for col name, col dtypes to construct further CREATE TABLE SQL query
        csv_file = StringIO(parsed_content)
        df = pd.read_csv(csv_file)
        df.columns = [c.lower() for c in df.columns]
        tbl_structure_data = {}
        for name, dtype in df.dtypes.items():
            dtype_name = str(dtype).lower()

            if dtype_name.startswith("bool"):
                sql_type = "BOOLEAN"
            elif dtype_name.startswith(("int", "uint")):
                sql_type = "BIGINT"
            elif dtype_name.startswith("float"):
                sql_type = "DOUBLE PRECISION"
            elif dtype_name.startswith("datetime"):
                sql_type = "TIMESTAMP"
            else:
                sql_type = "TEXT"

            tbl_structure_data[name.lower()] = sql_type

            columns_sql = ",\n\t\t\t".join(
                f'"{col}" {col_type}' for col, col_type in tbl_structure_data.items()
            )

        table_name = f"user_{np.random.randint(0, 10000000)}"
        sql_query = f"""
		CREATE TABLE IF NOT EXISTS public.{table_name}(
			_row_user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
			{columns_sql}
		)
		"""

        cursor.execute(sql_query)
        copy_sql = sql.SQL("""
		COPY {schema}.{table}
        ({cols}) FROM STDIN WITH 
        (
        FORMAT CSV,
        HEADER TRUE,
		DELIMITER ',',
		NULL ''
        )
""").format(
            schema=sql.Identifier("public"),
            table=sql.Identifier(table_name),
            cols=sql.SQL(", ").join(sql.Identifier(c) for c in df.columns),
        )
        db_obj.connection.commit()

        buffer = StringIO()
        df.to_csv(buffer, index=False, header=True)
        buffer.seek(0)
        cursor.copy_expert(copy_sql.as_string(db_obj.connection), buffer)
        print("after copy:", db_obj.connection.closed)
        # fetch the context
        context = db_obj.collect_context(schema_name="public", table_name=table_name)
        print("after context:", db_obj.connection.closed)
        db_obj.connection.commit()

        # make a db call
        record = ContextTbl(upload_id=upload_id, table_name=table_name, context=context)
        session.add(record)
        session.commit()
        session.refresh(record)

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "FileName": file.filename,
                "Size(MB)": round(total / (1024 * 1024), 2),
                "Details": "File Accepted For Processing",
                "table_name": table_name,
                "upload_id": str(upload_id),
            },
        )

    except UnicodeDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File must be UTF-8 encoded")
    except pd.errors.ParserError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not parse CSV")
    except pd.errors.EmptyDataError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CSV file is empty")
    except Exception:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "We couldn't complete the CSV import due to a server issue. Please try again.",
        )
    finally:
        if db_obj.connection:
            db_obj.connection.close()
        if cursor:
            cursor.close()


@sql_router.post("/ask")
def ask_to_agent(request: AskRequest, session: Session = Depends(yeild_session)):
    record = session.get(ContextTbl, request.upload_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requires Upload Id To Process further",
        )
    input_schema = {
        "messages": [],
        "user_query": request.question,
        "curated_prompt": "",
        "context_prompt_query": record.context,
        "generated_sql_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_response": "",
    }
    try:
        res = sql_analyst.invoke(input_schema)
        return {
            "answer": res["final_response"],
            "sql": res["generated_sql_query"],
        }
    except Exception as e:
        _logger.exception(f"Agent failed. Reason: {e}")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Could not process your question, please try again",
        )
