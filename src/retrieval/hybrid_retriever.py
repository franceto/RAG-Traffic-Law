import re
import unicodedata
import json
from pathlib import Path
from src.rewrite.query_rewriter import rewrite_query
from src.retrieval.bm25_search import search_bm25
from src.retrieval.exact_search import exact_search
from src.rewrite.vehicle_detector import detect_vehicle_group

STOP = {
    "xe", "may", "oto", "o", "to", "phat", "bao", "nhieu", "co", "bi",
    "khong", "la", "thi", "sao", "the", "nao", "muc", "tien", "hoi",
    "nguoi", "dieu", "khien", "quy", "dinh"
}

CONCEPTS = {
    "passenger_cabin": ["buong lai", "so luong"],
    "lane_change": ["chuyen lan"],
    "yielding": ["nhuong duong"],
    "intersection": ["giao nhau"],
    "accident_escape": ["tai nan", "va cham", "khong dung", "khong giu nguyen hien truong", "khong tro giup", "bo chay", "chay tron"],
    "traffic_light": ["den tin hieu", "den giao thong", "vuot den", "chay den", "khong chap hanh hieu lenh cua den tin hieu"],
    "green_light": ["den xanh"],
    "red_light": ["den do"],
    "yellow_light": ["den vang"],
    "horn_time": ["su dung coi", "bam coi", "22 gio", "05 gio", "5 gio"],
    "highway": ["cao toc"]
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


def detect_vehicle(query):
    return detect_vehicle_group(query)

def active_concepts(text):
    t = normalize(text)
    found = set()

    for name, terms in CONCEPTS.items():
        if any(term in t for term in terms):
            found.add(name)

    return found

def legal_query_ok(original, legal_query):
    original_concepts = active_concepts(original)
    query_concepts = active_concepts(legal_query)

    must_keep = {
        "passenger_cabin",
        "lane_change",
        "yielding",
        "accident_escape",
        "traffic_light",
        "green_light",
        "red_light",
        "yellow_light",
        "horn_time"
    }

    for c in original_concepts & must_keep:
        if c in ["red_light", "yellow_light"]:
            if "traffic_light" not in query_concepts and c not in query_concepts:
                return False
            continue

        if c not in query_concepts:
            return False

    if "highway" not in original_concepts and "highway" in query_concepts:
        return False

    return True

def evidence_supports(original, row):
    q_vehicle = detect_vehicle(original)
    r_vehicle = row.get("vehicle_group", "")

    if q_vehicle != "unknown":
        if not r_vehicle:
            return False
        if q_vehicle != r_vehicle:
            return False

    q_concepts = active_concepts(original)
    content_concepts = active_concepts(row.get("content", ""))

    if "green_light" in q_concepts:
        return False

    must_support = {
        "passenger_cabin",
        "lane_change",
        "yielding",
        "accident_escape",
        "traffic_light",
        "red_light",
        "yellow_light",
        "horn_time"
    }

    for c in q_concepts & must_support:
        if c in ["red_light", "yellow_light"]:
            if "traffic_light" not in content_concepts and c not in content_concepts:
                return False
            continue

        if c not in content_concepts:
            return False

    if "highway" not in q_concepts and "highway" in content_concepts:
        return False

    return True

def support_score(original, legal_query, row):
    content = normalize(row.get("content", ""))
    q_terms = set(tokens(original))
    l_terms = set(tokens(legal_query))

    q_overlap = len([t for t in q_terms if t in content])
    l_overlap = len([t for t in l_terms if t in content])

    return q_overlap + l_overlap
import json
from pathlib import Path

def highway_fallback(query, top_k=5):
    q = normalize(query)
    v = detect_vehicle(query)

    if "cao toc" not in q or "di vao" not in q:
        return []

    if v not in ["motorbike", "pedestrian", "bicycle"]:
        return []

    p = Path("data/chunks/legal_chunks.jsonl")
    if not p.exists():
        return []

    rows = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        row = json.loads(line)
        c = normalize(row.get("content", ""))
        if row.get("vehicle_group") != v:
            continue
        if "cao toc" not in c or "di vao" not in c:
            continue
        if "tai nan" not in q and "gay tai nan" in c:
            continue
        item = dict(row)
        item["score"] = 9999.0
        item["source_query"] = query
        item["rewrite"] = {"mode": "highway_fallback"}
        rows.append(item)

    return rows[:top_k]

def retrieve(query, top_k=5):
    exact_results = [
        r for r in exact_search(query, top_k=top_k)
        if evidence_supports(query, r)
    ]

    if exact_results:
        return {
            "query": query,
            "rewrite": {
                "original_query": query,
                "vehicle_group": detect_vehicle(query),
                "legal_queries": [query],
                "mode": "exact_first"
            },
            "results": exact_results[:top_k]
        }
    fallback_results = highway_fallback(query, top_k)
    if fallback_results:
        return {
            "query": query,
            "rewrite": {
                "original_query": query,
                "vehicle_group": detect_vehicle(query),
                "legal_queries": [query],
                "mode": "highway_fallback"
            },
            "results": fallback_results[:top_k]
        }
    rewrite = rewrite_query(query)
    legal_queries = [
        q for q in rewrite.get("legal_queries", [query])
        if legal_query_ok(query, q)
    ]

    if not legal_queries:
        legal_queries = [query]

    merged = {}

    for qi, legal_query in enumerate(legal_queries):
        for row in search_bm25(legal_query, top_k=15):
            if not evidence_supports(query, row):
                continue

            sup = support_score(query, legal_query, row)
            if sup < 4:
                continue

            key = row.get("citation", "")
            if not key:
                continue

            score = row.get("score", 0)
            score += sup * 6
            score += max(0, 8 - qi)

            item = dict(row)
            item["score"] = float(score)
            item["source_query"] = legal_query
            item["rewrite"] = rewrite

            if key not in merged or item["score"] > merged[key]["score"]:
                merged[key] = item

    results = sorted(merged.values(), key=lambda x: x["score"], reverse=True)

    if not results:
        results = highway_fallback(query, top_k)

    return {
        "query": query,
        "rewrite": rewrite,
        "results": results[:top_k]
    }
