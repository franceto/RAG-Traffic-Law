import json
import re
import unicodedata
from collections import defaultdict
from src.config.settings import settings

STOP = {
    "xe", "may", "oto", "o", "to", "co", "bi", "khong", "la", "thi",
    "sao", "the", "nao", "toi", "em", "anh", "chi", "phat", "bao",
    "nhieu", "muc", "tien", "hoi", "nguoi", "dieu", "khien"
}

QUERY_CONCEPTS = {
    "traffic_light": [
        "den tin hieu",
        "den giao thong",
        "vuot den",
        "chay den",
        "den do",
        "den vang",
        "den xanh"
    ],
    "red_light": ["den do"],
    "yellow_light": ["den vang"],
    "green_light": ["den xanh"],
    "priority_vehicle": [
        "xe cap cuu",
        "xe uu tien",
        "xe chua chay",
        "doan xe uu tien"
    ],
    "yield_priority_vehicle": [
        "nhuong duong cho xe cap cuu",
        "nhuong duong cho xe uu tien",
        "nhuong duong"
    ],
    "phat_nguoi": [
        "phat nguoi",
        "camera"
    ],
    "emergency_medical": [
        "cap cuu",
        "cho nguoi di cap cuu",
        "cho nguoi benh"
    ],
    "stop_line_signal": [
        "chom qua vach",
        "qua vach",
        "vach",
        "chua kip het nga tu",
        "sang den do"
    ],
    "ambiguous_signal": [
        "den xanh con",
        "sang den do",
        "chua kip",
        "nga tu"
    ],
    "alcohol_check": [
        "nong do con",
        "thoi nong do con",
        "kiem tra nong do con"
    ]
}

RELATED = {
    "red_light": ["traffic_light"],
    "yellow_light": ["traffic_light"],
    "green_light": ["traffic_light"],
    "priority_vehicle": ["yield_priority_vehicle"],
    "emergency_medical": ["priority_vehicle"],
    "ambiguous_signal": ["traffic_light", "stop_line_signal"]
}

def strip_accents(text):
    text = str(text or "").lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")

def normalize(text):
    text = strip_accents(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())

def tokens(text):
    return [t for t in normalize(text).split() if len(t) >= 2 and t not in STOP]

def load_graph():
    with settings.graph_file.open("r", encoding="utf-8") as f:
        return json.load(f)

def detect_query_concepts(query):
    q = normalize(query)
    concepts = set()

    for concept, terms in QUERY_CONCEPTS.items():
        if any(t in q for t in terms):
            concepts.add(concept)

    for c in list(concepts):
        for r in RELATED.get(c, []):
            concepts.add(r)

    return concepts

def score_content(query, row):
    q_terms = set(tokens(query))
    content = normalize(row.get("content", ""))
    return len([t for t in q_terms if t in content])

def graph_retrieve(query, top_k=8):
    graph = load_graph()
    concepts = detect_query_concepts(query)

    concept_to_citations = graph.get("concept_to_citations", {})
    citation_to_row = graph.get("citation_to_row", {})

    scores = defaultdict(float)
    reasons = defaultdict(list)

    for concept in concepts:
        citations = concept_to_citations.get(concept, [])

        for citation in citations:
            if concept in ["traffic_light", "priority_vehicle", "yield_priority_vehicle"]:
                weight = 30
            elif concept in ["red_light", "yellow_light", "green_light"]:
                weight = 18
            elif concept in ["phat_nguoi", "emergency_medical", "ambiguous_signal", "stop_line_signal"]:
                weight = 15
            else:
                weight = 10

            scores[citation] += weight
            reasons[citation].append(concept)

    for citation, row in citation_to_row.items():
        overlap = score_content(query, row)
        if overlap > 0:
            scores[citation] += overlap * 3
            reasons[citation].append("token_overlap")

    results = []

    for citation, score in scores.items():
        row = citation_to_row.get(citation)
        if not row:
            continue

        item = dict(row)
        item["score"] = float(score)
        item["retriever"] = "graph"
        item["graph_concepts"] = sorted(list(set(reasons[citation])))
        item["source_query"] = query
        results.append(item)

    results = sorted(results, key=lambda x: x["score"], reverse=True)
    return {
        "query": query,
        "query_concepts": sorted(list(concepts)),
        "results": results[:top_k]
    }
