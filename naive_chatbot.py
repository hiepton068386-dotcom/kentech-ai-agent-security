import ollama

client = ollama.Client(host="http://192.168.100.220:11434")
MODEL = "qwen2.5:7b"

def chatbot(user_message: str) -> str:
    """Chatbot đơn giản: 1 round-trip, không tool, không memory."""
    response = client.chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "Bạn là AI assistant của KenTech AI Solutions, "
                           "một công ty cybersecurity và AI automation tại Việt Nam."
                           "Bạn phải trả lời bằng tiếng Việt hoặc tiếng Anh. KHÔNG dùng ngôn ngữ khác."
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
    )
    return response["message"]["content"]

if __name__ == "__main__":
    print("=" * 60)
    print("NAIVE CHATBOT - Chứng minh giới hạn")
    print("=" * 60)

    # Test 1: Cần database
    print("\n[Test 1] Cần data từ DB:")
    q = "Tổng doanh thu tuần này của KenTech là bao nhiêu?"
    print(f"Q: {q}")
    print(f"A: {chatbot(q)}")

    # Test 2: Cần real-time
    print("\n[Test 2] Cần real-time info:")
    q = "Email mới nhất từ khách hàng hôm nay là gì?"
    print(f"Q: {q}")
    print(f"A: {chatbot(q)}")

    # Test 3: Cần thực thi action
    print("\n[Test 3] Cần thực thi action:")
    q = "Có email nào chưa xử lý không? Nếu có, gửi alert qua Telegram."
    print(f"Q: {q}")
    print(f"A: {chatbot(q)}")