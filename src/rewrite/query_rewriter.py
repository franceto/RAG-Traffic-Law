import os
import json
import re
import unicodedata
from dotenv import load_dotenv
from openai import OpenAI
from src.config.settings import settings

load_dotenv()

def strip_accents(text):
    text = str(text or "").lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")

def normalize(text):
    text = strip_accents(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())

def tokenize(text):
    stop = {
        "phat", "bao", "nhieu", "muc", "bi", "co", "khong", "la",
        "thi", "sao", "the", "nao", "tien", "hoi", "toi", "em",
        "anh", "chi", "a", "xe"
    }
    return [t for t in normalize(text).split() if len(t) >= 2 and t not in stop]

def load_mapping():
    p = settings.indexes_dir / "mapping_dictionary.json"
    return json.loads(p.read_text(encoding="utf-8"))

def detect_vehicle(query, mapping):
    q = normalize(query)

    for vehicle, aliases in mapping.get("vehicle_aliases", {}).items():
        for alias in aliases:
            if normalize(alias) in q:
                return vehicle

    return "unknown"

def expand_colloquial(query, mapping):
    q_norm = normalize(query)
    expanded = [query]

    for k, vals in mapping.get("colloquial_aliases", {}).items():
        if normalize(k) in q_norm:
            expanded.extend(vals)

    if "den xanh" in q_norm:
        return expanded

    if "vuot den do" in q_norm or "chay den do" in q_norm or "vuot den" in q_norm:
        expanded.append("không chấp hành hiệu lệnh của đèn tín hiệu giao thông")

    if "vuot den vang" in q_norm or "chay den vang" in q_norm:
        expanded.append("không chấp hành hiệu lệnh của đèn tín hiệu giao thông")

    if any(x in q_norm for x in ["va cham", "tai nan"]) and any(x in q_norm for x in ["chay tron", "bo chay", "chay di tron", "roi hien truong"]):
        expanded.extend([
            "có liên quan trực tiếp đến vụ tai nạn giao thông mà không dừng lại",
            "không giữ nguyên hiện trường",
            "không trợ giúp người bị nạn"
        ])

    if "quen bang" in q_norm or "khong mang bang" in q_norm:
        expanded.append("không xuất trình được giấy phép lái xe")

    if "ca vet" in q_norm or "cavet" in q_norm or "dang ky xe" in q_norm:
        expanded.append("không xuất trình được chứng nhận đăng ký xe")

    if "bao hiem" in q_norm:
        expanded.append("không có hoặc không mang theo chứng nhận bảo hiểm bắt buộc trách nhiệm dân sự")

    return expanded

def mapping_score(query, entry, vehicle_group, mapping):
    q_text = " ".join(expand_colloquial(query, mapping))
    q_tokens = set(tokenize(q_text))
    e_tokens = set(entry.get("keywords", [])) | set(tokenize(entry.get("legal_phrase", "")))

    if not q_tokens or not e_tokens:
        return 0

    score = len(q_tokens & e_tokens) * 4

    pn = entry.get("normalized_phrase", "")

    for raw in expand_colloquial(query, mapping):
        rn = normalize(raw)
        if rn and rn in pn:
            score += 20

    if entry.get("vehicle_group") == vehicle_group:
        score += 10
    elif vehicle_group != "unknown" and entry.get("vehicle_group"):
        score -= 12

    if "cao toc" not in normalize(query) and "duong_cao_toc" in entry.get("condition_tags", []):
        score -= 12

    if "den xanh" in normalize(query):
        if "den do" in pn or "khong chap hanh hieu lenh cua den tin hieu" in pn:
            score -= 40

    return score

def top_mapping_candidates(query, top_k=8, min_score=10):
    mapping = load_mapping()
    vehicle_group = detect_vehicle(query, mapping)

    if "den xanh" in normalize(query):
        return vehicle_group, []

    scored = []

    for e in mapping.get("entries", []):
        s = mapping_score(query, e, vehicle_group, mapping)
        if s >= min_score:
            e2 = dict(e)
            e2["mapping_score"] = s
            scored.append(e2)

    scored = sorted(scored, key=lambda x: x["mapping_score"], reverse=True)
    return vehicle_group, scored[:top_k]

def llm_enabled():
    return os.getenv("ENABLE_LLM_REWRITE", "1").strip() == "1"

def get_client():
    if not llm_enabled():
        return None, ""

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key and not openai_key.startswith("your_"):
        return OpenAI(api_key=openai_key), os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key and not groq_key.startswith("your_"):
        return OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1"), os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    return None, ""

def contradictory(original, text):
    o = normalize(original)
    t = normalize(text)

    if "cao toc" not in o and "cao toc" in t:
        return True

    if "den xanh" in o and any(x in t for x in ["den do", "trang thai do", "khong chap hanh hieu lenh cua den tin hieu"]):
        return True

    if not any(x in o for x in ["tai nan", "va cham", "bo chay", "chay tron", "chay di tron", "hien truong"]):
        if any(x in t for x in ["tai nan giao thong", "khong giu nguyen hien truong", "khong tro giup nguoi bi nan"]):
            return True

    return False

def clean_legal_queries(query, items):
    out = []

    for x in items:
        s = str(x or "").strip()
        sn = normalize(s)

        if not s:
            continue

        if contradictory(query, s):
            continue

        if re.search(r"\bdieu\s+\d+|\bkhoan\s+\d+|\bdiem\s+[a-z]", sn):
            continue

        if re.search(r"\d{1,3}(?:\.\d{3})+\s*dong", sn):
            continue

        if len(s) > 280:
            continue

        out.append(s)

    return list(dict.fromkeys(out))[:6]

def llm_rewrite(query, candidates, vehicle_group):
    if not candidates:
        return None

    client, model = get_client()
    if client is None:
        return None

    compact = [
        {
            "vehicle_group": c["vehicle_group"],
            "legal_phrase": c["legal_phrase"],
            "condition_tags": c["condition_tags"]
        }
        for c in candidates[:5]
    ]

    prompt = f"""
Chuyển câu hỏi đời thường sang 3-5 truy vấn pháp lý để phục vụ RAG.

Câu hỏi:
{query}

vehicle_group:
{vehicle_group}

Cụm pháp lý tham khảo:
{json.dumps(compact, ensure_ascii=False, indent=2)}

Quy tắc:
- Chỉ dùng cụm pháp lý phù hợp với câu hỏi.
- Không sinh mức phạt.
- Không sinh điều/khoản/điểm.
- Không thêm điều kiện không có trong câu hỏi.
- Nếu không chắc, giữ gần nguyên câu hỏi.
- Trả JSON:
{{"legal_queries": ["..."], "vehicle_group": "car|motorbike|bicycle|pedestrian|unknown"}}
"""

    try:
        res = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Bạn chỉ viết lại truy vấn pháp lý cho hệ thống RAG."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=700,
            response_format={"type": "json_object"}
        )
        return json.loads(res.choices[0].message.content)
    except Exception as e:
        print("LLM_REWRITE_FALLBACK:", e)
        return None

def fallback_rewrite(query, candidates):
    mapping = load_mapping()
    queries = expand_colloquial(query, mapping)

    if candidates:
        queries.append(candidates[0]["legal_phrase"])

    return queries

def rewrite_query(query):
    vehicle_group, candidates = top_mapping_candidates(query, top_k=8)

    llm_data = llm_rewrite(query, candidates, vehicle_group)
    queries = []

    if llm_data:
        llm_vehicle = llm_data.get("vehicle_group", vehicle_group)

        if vehicle_group == "unknown" and llm_vehicle in ["car", "motorbike", "bicycle", "pedestrian", "unknown"]:
            vehicle_group = llm_vehicle

        queries.extend(llm_data.get("legal_queries", []))
        queries.extend([c["legal_phrase"] for c in candidates[:2]])
        queries.insert(0, query)
    else:
        queries = fallback_rewrite(query, candidates)

    legal_queries = clean_legal_queries(query, queries)

    return {
        "original_query": query,
        "vehicle_group": vehicle_group,
        "legal_queries": legal_queries,
        "mapping_candidates": candidates
    }
