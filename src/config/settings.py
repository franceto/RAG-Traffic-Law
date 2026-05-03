from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    project_root: Path = Path(__file__).resolve().parents[2]

    raw_dir: Path = project_root / "data" / "raw"
    processed_dir: Path = project_root / "data" / "processed"
    chunks_dir: Path = project_root / "data" / "chunks"
    indexes_dir: Path = project_root / "data" / "indexes"
    logs_dir: Path = project_root / "logs"

    chunk_file: Path = chunks_dir / "legal_chunks.jsonl"

    bm25_index_file: Path = indexes_dir / "bm25_index.pkl"
    graph_file: Path = indexes_dir / "legal_graph.json"

    embedding_model: str = "bkai-foundation-models/vietnamese-bi-encoder"

    openai_model: str = "gpt-4o-mini"
    groq_model: str = "llama-3.1-8b-instant"

    top_k_bm25: int = 20
    top_k_dense: int = 20
    top_k_graph: int = 20
    final_top_k: int = 5

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()