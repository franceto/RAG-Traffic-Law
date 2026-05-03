import json
import re
from src.config.settings import settings

DIEU = "\u0110i\u1ec1u"
PHAT_TIEN_TU = "Ph\u1ea1t ti\u1ec1n t\u1eeb"
DONG = "\u0111\u1ed3ng"

def norm_text(text):
    text = str(text or "")
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()

def detect_doc_id(name):
    s = name.lower()
    if "168" in s:
        return "168/2024/NĐ-CP", "Nghị định 168/2024/NĐ-CP"
    if "36" in s or "ttatgt" in s:
        return "36/2024/QH15", "Luật Trật tự, an toàn giao thông đường bộ 2024"
    return name, name

def split_articles(text):
    text = norm_text(text)
    pattern = re.compile(rf"(?m)^\s*{DIEU}\s+(\d+)\.\s*(.+)$")
    ms = list(pattern.finditer(text))
    rows = []

    for i, m in enumerate(ms):
        start = m.start()
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)

        rows.append({
            "article_no": m.group(1),
            "article": f"{DIEU} {m.group(1)}",
            "article_title": m.group(2).strip(),
            "text": text[start:end].strip()
        })

    return rows

def split_clauses(article_text):
    text = norm_text(article_text)
    pattern = re.compile(r"(?m)^\s*(\d+)\.\s+")
    ms = list(pattern.finditer(text))
    rows = []

    for i, m in enumerate(ms):
        start = m.start()
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        rows.append({
            "clause": m.group(1),
            "text": text[start:end].strip()
        })

    return rows

def split_points(clause_text):
    text = norm_text(clause_text)
    pattern = re.compile(r"(?m)^\s*([a-z\u0111])\s*\)\s+")
    ms = list(pattern.finditer(text))
    rows = []

    for i, m in enumerate(ms):
        start = m.start()
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        rows.append({
            "point": m.group(1),
            "text": text[start:end].strip()
        })

    return rows


def normalize_money(s):
    s = str(s or "")
    s = re.sub(r"(?<=\d)\s+(?=\d)", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def fine_text_from_clause(text):
    text = norm_text(text)
    pattern = rf"({PHAT_TIEN_TU}\s+[\d\s\.,]+\s*{DONG}\s+\u0111\u1ebfn\s+[\d\s\.,]+\s*{DONG})"
    m = re.search(pattern, text, flags=re.I)
    return normalize_money(m.group(1)) if m else ""

def vehicle_group(article_no, article_title):
    s = article_title.lower()

    if article_no == "6":
        return "car"
    if article_no == "7":
        return "motorbike"
    if article_no == "8":
        return "special_vehicle"
    if article_no == "9":
        return "bicycle"
    if article_no == "10":
        return "pedestrian"

    return ""

def topic_of(text):
    return "traffic_violation_penalty" if PHAT_TIEN_TU.lower() in text.lower() else "traffic_law"

def make_citation(doc_id, article, clause="", point=""):
    parts = [doc_id, article]
    if clause:
        parts.append(f"Khoản {clause}")
    if point:
        parts.append(f"Điểm {point}")
    return " - ".join(parts)

def build_chunks_from_file(path):
    text = norm_text(path.read_text(encoding="utf-8", errors="ignore"))
    doc_id, doc_title = detect_doc_id(path.stem)
    chunks = []

    articles = split_articles(text)
    print("ARTICLES:", path.name, len(articles))

    for art in articles:
        clauses = split_clauses(art["text"])
        vg = vehicle_group(art["article_no"], art["article_title"])

        for cl in clauses:
            fine = fine_text_from_clause(cl["text"])
            points = split_points(cl["text"])

            if points:
                first_pos = min([cl["text"].find(p["text"]) for p in points if cl["text"].find(p["text"]) >= 0] or [0])
                clause_intro = cl["text"][:first_pos].strip()

                for pt in points:
                    content = norm_text("\n".join([
                        f'{art["article"]}. {art["article_title"]}',
                        clause_intro,
                        pt["text"]
                    ]))

                    chunks.append({
                        "doc_id": doc_id,
                        "doc_title": doc_title,
                        "source_file": path.name,
                        "article": art["article"],
                        "article_title": art["article_title"],
                        "clause": cl["clause"],
                        "point": pt["point"],
                        "citation": make_citation(doc_id, art["article"], cl["clause"], pt["point"]),
                        "topic": topic_of(content),
                        "vehicle_group": vg,
                        "fine_text": fine,
                        "content": content
                    })
            else:
                content = norm_text(cl["text"])
                chunks.append({
                    "doc_id": doc_id,
                    "doc_title": doc_title,
                    "source_file": path.name,
                    "article": art["article"],
                    "article_title": art["article_title"],
                    "clause": cl["clause"],
                    "point": "",
                    "citation": make_citation(doc_id, art["article"], cl["clause"], ""),
                    "topic": topic_of(content),
                    "vehicle_group": vg,
                    "fine_text": fine,
                    "content": content
                })

    return chunks

def build_all_chunks():
    settings.chunks_dir.mkdir(parents=True, exist_ok=True)
    rows = []

    for path in sorted(settings.processed_dir.glob("*.txt")):
        chunks = build_chunks_from_file(path)
        print("FILE:", path.name, "CHUNKS:", len(chunks))
        rows.extend(chunks)

    with settings.chunk_file.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("SAVED:", settings.chunk_file)
    print("TOTAL_CHUNKS:", len(rows))

if __name__ == "__main__":
    build_all_chunks()
