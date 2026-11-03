"""Run from the project root: python -m uvicorn backend.main:app."""

import asyncio
from contextlib import asynccontextmanager
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from langgraph.errors import GraphRecursionError
from pydantic import BaseModel, Field

from backend.agent import SalesAgent


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "").strip()
    app.state.agent = (
        SalesAgent(api_key, model, os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp"))
        if api_key and model else None
    )
    yield


app = FastAPI(title="Sales Agent API", lifespan=lifespan)


class AnalyzeRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)


class AnalyzeResponse(BaseModel):
    answer: str


@app.get("/health")
async def health(request: Request):
    return {"status": "ok", "agent_configured": request.app.state.agent is not None}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(body: AnalyzeRequest, request: Request):
    if not body.prompt.strip():
        raise HTTPException(422, "Prompt must not be blank.")
    agent = request.app.state.agent
    if agent is None:
        raise HTTPException(503, "Set OPENAI_API_KEY and OPENAI_MODEL in the backend environment.")
    try:
        answer = await asyncio.wait_for(agent.analyze(body.prompt.strip()), timeout=90)
    except TimeoutError:
        raise HTTPException(504, "Sales analysis timed out. Please try again.") from None
    except GraphRecursionError:
        raise HTTPException(502, "The agent reached its step limit.") from None
    except Exception:
        # Do not return upstream exception text, which may contain credentials.
        raise HTTPException(502, "Sales analysis failed. Check model access and MCP availability.") from None
    return AnalyzeResponse(answer=answer)
