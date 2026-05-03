from src.retrieval.hybrid_retriever import retrieve
from src.llm.answer_generator import generate_answer
from src.rewrite.query_type_classifier import classify_query_type, is_green_light_question
from src.graph.graph_retriever import graph_retrieve
from src.llm.graph_answer_generator import generate_graph_answer
from src.rag.multi_vehicle_answer import multi_vehicle_answer
from src.rewrite.vehicle_detector import (
    detect_vehicle_group,
    needs_vehicle_clarification
)

def keep_best_evidence(results):
    if not results:
        return []

    top = results[0]

    if top.get("fine_text") and top.get("citation"):
        return [top]

    return results[:5]

def sanitize_related_sources(results):
    clean = []

    for r in results[:5]:
        x = dict(r)
        x["fine_text"] = ""
        clean.append(x)

    return clean

def non_violation_answer(question):
    return (
        "Tôi chưa tìm thấy căn cứ xử phạt trực tiếp đối với hành vi được mô tả là vượt đèn tín hiệu màu xanh. "
        "Trong dữ liệu hiện có, nhóm hành vi bị xử phạt thường liên quan đến việc không chấp hành hiệu lệnh của đèn tín hiệu giao thông. "
        "Nếu tình huống thực tế là xe đi qua vạch khi đèn đã chuyển đỏ hoặc vàng, bạn cần mô tả rõ thời điểm xe qua vạch và loại phương tiện để xác định đúng căn cứ."
    )

def answer_question(question, top_k=5):
    if is_green_light_question(question):
        vehicle_group = detect_vehicle_group(question)
        return {
            "question": question,
            "query_type": "non_violation_question",
            "vehicle_group": vehicle_group,
            "needs_clarification": False,
            "answer": non_violation_answer(question),
            "rewrite": {
                "original_query": question,
                "mode": "non_violation_guard"
            },
            "sources": [],
            "retrieved_count": 0
        }

    query_type = classify_query_type(question)
    vehicle_group = detect_vehicle_group(question)

    if query_type == "non_violation_question":
        return {
            "question": question,
            "query_type": query_type,
            "vehicle_group": vehicle_group,
            "needs_clarification": False,
            "answer": non_violation_answer(question),
            "rewrite": {
                "original_query": question,
                "mode": "non_violation_guard"
            },
            "sources": [],
            "retrieved_count": 0
        }

    if needs_vehicle_clarification(question, query_type):
        answer, sources, rows = multi_vehicle_answer(question)

        return {
            "question": question,
            "query_type": query_type,
            "vehicle_group": vehicle_group,
            "needs_clarification": True,
            "clarification_fields": ["vehicle_group"],
            "answer": answer,
            "rewrite": {
                "original_query": question,
                "mode": "multi_vehicle_clarification",
                "vehicle_options": [r["vehicle_name"] for r in rows]
            },
            "sources": sources,
            "retrieved_count": len(sources)
        }

    if query_type in ["exception_question", "ambiguous_scenario", "rule_question"]:
        gout = graph_retrieve(question, top_k=top_k)
        raw_results = gout.get("results", [])
        results = sanitize_related_sources(raw_results)
        answer = generate_graph_answer(question, results, query_type)

        return {
            "question": question,
            "query_type": query_type,
            "vehicle_group": vehicle_group,
            "needs_clarification": False,
            "answer": answer,
            "rewrite": {
                "original_query": question,
                "mode": "graphrag",
                "query_concepts": gout.get("query_concepts", [])
            },
            "sources": results,
            "retrieved_count": len(results)
        }

    out = retrieve(question, top_k=top_k)
    results = keep_best_evidence(out.get("results", []))
    answer = generate_answer(question, results)

    return {
        "question": question,
        "query_type": query_type,
        "vehicle_group": vehicle_group,
        "needs_clarification": False,
        "answer": answer,
        "rewrite": out.get("rewrite", {}),
        "sources": results,
        "retrieved_count": len(results)
    }
