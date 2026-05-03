def clean_text(text):
    return " ".join(str(text or "").split())

def top1_answer(question, result):
    fine = clean_text(result.get("fine_text", ""))
    citation = clean_text(result.get("citation", ""))
    content = clean_text(result.get("content", ""))

    if not citation or not content:
        return "Tôi chưa tìm thấy căn cứ pháp lý phù hợp trong dữ liệu hiện có để kết luận."

    if fine:
        return (
            f"{fine}.\n\n"
            f"Căn cứ pháp lý: {citation}.\n\n"
            f"Nội dung liên quan: {content}"
        )

    return (
        "Tôi tìm thấy căn cứ pháp lý liên quan nhưng nguồn chưa nêu rõ mức phạt.\n\n"
        f"Căn cứ pháp lý: {citation}.\n\n"
        f"Nội dung liên quan: {content}"
    )

def generate_answer(question, results):
    if not results:
        return "Tôi chưa tìm thấy căn cứ pháp lý phù hợp trong dữ liệu hiện có để kết luận."

    return top1_answer(question, results[0])
