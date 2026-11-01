from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.sql_analyst_router import sql_router
from contextlib import asynccontextmanager
from utils.db_connection import create_tbls

from apscheduler.schedulers.background import BackgroundScheduler
from utils.cleanup import cleanup_expired_table

from pathlib import Path

scheduler = BackgroundScheduler()



@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application Started")
    create_tbls()
    print("Tables Created")
    cleanup_expired_table()
    scheduler.add_job(
        cleanup_expired_table,
        "cron",
        hour=10,
        minute=0,
        id="daily_cleanup_10am",
        replace_existing=True,
        misfire_grace_time=3600,
        coalesce=True,
    )
    scheduler.start()
    yield
    print("Application Closed")
    scheduler.shutdown()


app = FastAPI(
    title="Ola Data Agent API Docs",
    description="Comprehensive API docs for ola agent.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(router=sql_router)


