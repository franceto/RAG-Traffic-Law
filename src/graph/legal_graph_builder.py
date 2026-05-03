import json
import re
import unicodedata
from collections import defaultdict
from src.config.settings import settings

CONCEPT_PATTERNS = {
    "traffic_light": [
        "den tin hieu",
        "den giao thong",
        "khong chap hanh hieu lenh cua den tin hieu"
    ],
    "red_light": ["den do"],
    "yellow_light": ["den vang"],
    "green_light": ["den xanh"],
    "priority_vehicle": [
        "xe uu tien",
        "xe duoc quyen uu tien",
        "xe cap cuu",
        "xe chua chay",
        "phat tin hieu uu tien"
    ],
    "yield_priority_vehicle": [
        "nhuong duong cho xe duoc quyen uu tien",
        "khong nhuong duong cho xe duoc quyen uu tien",
        "xe duoc quyen uu tien dang phat tin hieu uu tien",
        "xe uu tien dang phat tin hieu"
    ],
    "phat_nguoi": [
        "phat nguoi",
        "camera",
        "hinh anh"
    ],
    "accident": [
        "tai nan giao thong",
        "va cham",
        "nguoi bi nan"
    ],
    "emergency_medical": [
        "cap cuu",
        "nguoi benh di cap cuu",
        "cho nguoi benh di cap cuu"
    ],
    "stop_line_signal": [
        "vach",
        "qua vach",
        "dung truoc vach",
        "vach dung xe"
    ],
    "alcohol_check": [
        "nong do con",
        "hoi tho",
        "miligam"
    ],
    "fine": [
        "phat tien tu"
    ],
    "temporary_seizure": [
        "tam giu phuong tien",
        "tam giu giay to"
    ],
    "license_point": [
        "tru diem giay phep lai xe",
        "phuc hoi diem giay phep lai xe"
    ]
}

def strip_accents(text):
    text = str(text or "").lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")

def normalize(text):
    text = strip_accents(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())

def load_chunks():
    with settings.chunk_file.open("r", encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]

def detect_concepts(text):
    n = normalize(text)
    concepts = []

    for concept, terms in CONCEPT_PATTERNS.items():
        if any(t in n for t in terms):
            concepts.append(concept)

    return concepts

def add_node(nodes, node_id, **attrs):
    if node_id not in nodes:
        nodes[node_id] = attrs
    else:
        nodes[node_id].update(attrs)

def add_edge(edges, src, dst, edge_type):
    edges.append({
        "source": src,
        "target": dst,
        "type": edge_type
    })

def build_legal_graph():
    rows = load_chunks()

    nodes = {}
    edges = []

    concept_to_citations = defaultdict(list)
    vehicle_to_citations = defaultdict(list)
    article_to_citations = defaultdict(list)
    citation_to_row = {}

    for row in rows:
        citation = row.get("citation", "")
        if not citation:
            continue

        chunk_id = f"chunk::{citation}"
        doc_id = f"doc::{row.get('doc_id', '')}"
        article_id = f"article::{row.get('doc_id', '')}::{row.get('article', '')}"
        vehicle = row.get("vehicle_group", "")
        vehicle_id = f"vehicle::{vehicle}" if vehicle else ""

        text = " ".join([
            row.get("citation", ""),
            row.get("fine_text", ""),
            row.get("content", "")
        ])

        concepts = detect_concepts(text)

        add_node(
            nodes,
            chunk_id,
            node_type="chunk",
            citation=citation,
            fine_text=row.get("fine_text", ""),
            vehicle_group=vehicle,
            article=row.get("article", ""),
            content=row.get("content", "")
        )

        add_node(nodes, doc_id, node_type="doc", doc_id=row.get("doc_id", ""))
        add_node(nodes, article_id, node_type="article", article=row.get("article", ""))

        add_edge(edges, chunk_id, doc_id, "belongs_to_doc")
        add_edge(edges, chunk_id, article_id, "belongs_to_article")

        if vehicle:
            add_node(nodes, vehicle_id, node_type="vehicle", vehicle_group=vehicle)
            add_edge(edges, chunk_id, vehicle_id, "has_vehicle")
            vehicle_to_citations[vehicle].append(citation)

        for concept in concepts:
            concept_id = f"concept::{concept}"
            add_node(nodes, concept_id, node_type="concept", concept=concept)
            add_edge(edges, chunk_id, concept_id, "has_concept")
            concept_to_citations[concept].append(citation)

        article_to_citations[row.get("article", "")].append(citation)
        citation_to_row[citation] = row

    graph = {
        "nodes": nodes,
        "edges": edges,
        "concept_to_citations": {k: list(dict.fromkeys(v)) for k, v in concept_to_citations.items()},
        "vehicle_to_citations": {k: list(dict.fromkeys(v)) for k, v in vehicle_to_citations.items()},
        "article_to_citations": {k: list(dict.fromkeys(v)) for k, v in article_to_citations.items()},
        "citation_to_row": citation_to_row,
        "stats": {
            "chunks": len(rows),
            "nodes": len(nodes),
            "edges": len(edges),
            "concepts": len(concept_to_citations)
        }
    }

    settings.indexes_dir.mkdir(parents=True, exist_ok=True)

    with settings.graph_file.open("w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print("SAVED:", settings.graph_file)
    print("CHUNKS:", len(rows))
    print("NODES:", len(nodes))
    print("EDGES:", len(edges))
    print("CONCEPTS:", len(concept_to_citations))

if __name__ == "__main__":
    build_legal_graph()
