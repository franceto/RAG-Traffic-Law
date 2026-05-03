import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.pipeline import answer_question

app = FastAPI(title="Traffic Law RAG")

app.mount("/assets", StaticFiles(directory=str(ASSETS)), name="assets")

class AskRequest(BaseModel):
    question: str

@app.get("/")
def home():
    return FileResponse(ASSETS / "index.html")

@app.post("/api/ask")
def ask(req: AskRequest):
    q = req.question.strip()
    if not q:
        return {"ok": False, "error": "EMPTY_QUESTION"}
    res = answer_question(q)
    return {"ok": True, "data": res}