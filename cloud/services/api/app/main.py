from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.db.session import engine
from app.routers import auth, commands, insights, live, nodes


@asynccontextmanager
def lifespan(app: FastAPI) -> AsyncIterator[None]:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    yield


app = FastAPI(title="VineGuard Cloud API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(nodes.router)
app.include_router(insights.router)
app.include_router(commands.router)
app.include_router(live.router)


@app.get("/")
def read_root():
    return {"status": "ok", "service": "vineguard-api"}
