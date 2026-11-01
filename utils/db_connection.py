import os

from sqlmodel import create_engine, SQLModel, Session
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("POSTGRES_DB_URL")

if not DB_URL:
    raise ValueError("Required DB URL")

engine = create_engine(url=DB_URL, echo=True)


def create_tbls():
    SQLModel.metadata.create_all(engine)


def yeild_session():
    with Session(engine) as session:
        yield session
