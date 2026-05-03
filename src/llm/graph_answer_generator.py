import re
import unicodedata

def clean_text(text):
    return " ".join(str(text or "").split())

def strip_accents(text):
    text = str(text or "").lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")

def norm(text):
    text = strip_accents(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())

def is_traffic_light_case(question):
    q = norm(question)
    keys = ["den do", "den vang", "den xanh", "den tin hieu", "den giao thong", "vuot den", "chay den"]
    return any(k in q for k in keys)

def format_sources(results):
    lines = []

    for i, r in enumerate(results, 1):
        citation = clean_text(r.get("citation", ""))
        fine = clean_text(r.get("fine_text", ""))
        content = clean_text(r.get("content", ""))

        if fine:
            lines.append(f"{i}. {citation}: {fine}. Nội dung: {content}")
        else:
            lines.append(f"{i}. {citation}: {content}")

    return "\n".join(lines)

def ambiguous_intro(question):
    if is_traffic_light_case(question):
        return (
            "Tình huống này phụ thuộc vào thời điểm xe qua vạch, trạng thái đèn tín hiệu "
            "và dữ liệu ghi nhận thực tế. "
        )

    return (
        "Tình huống này còn phụ thuộc vào tình tiết thực tế, chứng cứ ghi nhận "
        "và cách xác định hành vi vi phạm cụ thể. "
    )

def ambiguous_need_more(question):
    if is_traffic_light_case(question):
        return "Cần làm rõ thời điểm xe qua vạch, trạng thái đèn tín hiệu, camera ghi nhận và tình tiết thực tế."

    return "Cần làm rõ thêm hành vi cụ thể, bối cảnh xảy ra, chứng cứ ghi nhận và căn cứ pháp lý áp dụng."

def generate_graph_answer(question, results, query_type):
    if not results:
        if query_type == "exception_question":
            return (
                "Đây là tình huống có yếu tố ngoại lệ hoặc nhiều điều kiện. "
                "Tôi chưa tìm thấy đủ căn cứ pháp lý trực tiếp trong dữ liệu hiện có để kết luận chắc chắn. "
                "Cần bổ sung thêm quy định liên quan hoặc tình tiết thực tế cụ thể."
            )

        if query_type == "ambiguous_scenario":
            return (
                "Tình huống này còn mơ hồ nên tôi chưa đủ căn cứ pháp lý để kết luận. "
                f"{ambiguous_need_more(question)}"
            )

        return "Tôi chưa tìm thấy căn cứ pháp lý phù hợp trong dữ liệu hiện có để kết luận."

    src = format_sources(results[:5])

    if query_type == "exception_question":
        return (
            "Đây là tình huống có yếu tố ngoại lệ hoặc nhiều điều kiện. "
            "Tôi tìm thấy một số căn cứ pháp lý liên quan, nhưng chưa có căn cứ trực tiếp trong dữ liệu hiện có để khẳng định chắc chắn được miễn phạt hoặc bị phạt.\n\n"
            "Các căn cứ liên quan:\n"
            f"{src}\n\n"
            "Kết luận: Chưa đủ căn cứ pháp lý trực tiếp để kết luận chắc chắn. Cần bổ sung thêm tình tiết thực tế hoặc quy định liên quan."
        )

    if query_type == "ambiguous_scenario":
        return (
            f"{ambiguous_intro(question)}"
            "Tôi tìm thấy một số căn cứ liên quan, nhưng chưa đủ để kết luận trực tiếp.\n\n"
            "Các căn cứ liên quan:\n"
            f"{src}\n\n"
            f"Kết luận: Chưa đủ căn cứ pháp lý trực tiếp để kết luận. {ambiguous_need_more(question)}"
        )

    return src