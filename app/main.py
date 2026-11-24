from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.init_db import init_db
from app.api.routes import router
from app.services.ai import close_http_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    await close_http_client()

app = FastAPI(
    title="PS-22 Proactive Digital Engagement Agent",
    version="2.0.0",
    description="Customer engagement platform with MCP-connected customer intelligence tools.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
