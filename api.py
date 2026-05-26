from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from rag import answer_question

app = FastAPI(title="Central Church Counseling API")

_DEMO_HTML = Path(__file__).parent / "static" / "demo.html"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://central-church-website.vercel.app",
        "http://localhost:5173",
    ],
    allow_origin_regex=r"https://central-church-website-.*\.vercel\.app",
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/demo")
def demo() -> FileResponse:
    return FileResponse(_DEMO_HTML, media_type="text/html")


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    return AskResponse(answer=answer_question(req.question))
