import json
import sqlite3
from datetime import datetime, timedelta

import ollama

MODEL = "qwen2.5:7b"

def get_weekly_revenue(days: int = 7) -> dict:
    """Lấy doanh thu N ngày gần nhất từ DB."""
    conn = sqlite3.connect("kentech.db")    # mở database
    cursor = conn.cursor()

    # Tính ngày bắt đầu (hôm nay - N ngày)
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    cursor.execute(
        """
        SELECT
            SUM(amount) AS total_revenue, 
            COUNT(*) AS transaction_count,
            AVG(amount) AS avg_deal_size
        FROM transactions
        WHERE date >= ? AND status = 'complete'
        """,
        (start_date,),
    )

    row = cursor.fetchone() # lấy 1 dòng kết quả
    conn.close()

    return {
        "total_revenue_vnd":    round(row[0] or 0),
        "transaction_count":    row[1] or 0,
        "avg_deal_size_vnd":    round(row[2] or 0),
        "period_days":  days,  
        "start_date":   start_date,
    }

def get_pending_emails() -> dict:
    """Lấy danh sách email chưa xử lý."""
    conn = sqlite3.connect("kentech.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, sender, subject, received_at
        FROM emails
        WHERE status = 'pending'
        ORDER BY received_at DESC -- email mới nhất lên đầu
        """
    )

    rows = cursor.fetchall() # lấy tất cả dòng kết quả
    conn.close()

    return {
        "count": len(rows), # tổng số email pending
        "emails": [
            {
                "id":           row[0],
                "sender":       row[1],
                "subject":      row[2],
                "received_at":   row[3],
            }
            for row in rows # loop qua từng email
        ],
    }

def send_telegram_alert(message: str, priority: str = "normal") -> dict:
    """Gửi alert qua Telegram (mock — tuần 2 implement thật)."""
    timestamp = datetime.now().strftime("%H:%M:%S")

    # Chọn emoji theo mức độ ưu tiên
    emoji = {"low": "ℹ️", "normal": "📢", "high": "⚠️", "critical": "🚨"}.get(priority, "📢")

    print(f"\n {emoji} [TELEGRAM - {priority.upper()}] {timestamp}")
    print(f"    {message}")

    return {
        "status":       "sent",
        "priority":     priority,
        "timestamp":    timestamp,    
        "message":      message,
    }

TOOLS = {
    "get_weekly_revenue": {
        "function": get_weekly_revenue, # trỏ thẳng đến function ở Phần 2
        "schema": {
            "type": "function",
            "function": {
                "name": "get_weekly_revenue", # tên LLM sẽ gọi
                "description": ( 
                    "Lấy tổng doanh thu của KenTech trong N ngày gần nhất. "
                    "Dùng khi được hỏi về: doanh thu, revenue, thu nhập, tiền."
                ), # LLM đọc cái này để biết khi nào cần gọi tool này
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer", # kiểu dữ liệu: số nguyên
                            "description": "Số ngày cần lấy dữ liệu, mặc định 7",
                            "default": 7,
                        },
                    },
                },
            },
        },
    },

    "get_pending_emails": {
        "function": get_pending_emails,
        "schema": {
            "type": "function",
            "function": {
                "name": "get_pending_emails",
                "description": (
                    "Lấy danh sách email chưa xử lý. "
                    "Dùng khi được hỏi về: email mới, email chờ, inbox."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {}, # tool này không cần tham số gì
                },
            },
        },
    },

    "send_telegram_alert": {
        "function": send_telegram_alert,
        "schema": {
            "type": "function",
            "function": {
                "name": "send_telegram_alert",
                "description": (
                    "Gửi thông báo qua Telegram. "
                    "Dùng khi cần: thông báo, alert, gửi tin nhắn."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string", # kiểu dữ liệu: chuỗi text
                            "description": "Nội dung thông báo cần gửi",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "normal", "high", "critical"], # chỉ chấp nhận 4 giá trị này
                            "description": "Mức độ ưu tiên",
                            "default": "normal",
                        },
                    },
                    "required": ["message"], # message bắt buộc phải có, priority thì không
                },
            },
        },
    },
}

SYSTEM_PROMPT = """Bạn là AI agent của KenTech AI Solutions.

NGUYÊN TẮC BẮT BUỘC:
1. LUÔN dùng tool để lấy data thực tế trước khi trả lời
2. KHÔNG BAO GIỜ đoán, bịa, hoặc ước tính số liệu
3. Nếu không có tool phù hợp → trả lời: "Tôi không có tool để lấy thông tin này."
4. Số tiền format: X.XXX.XXX VNĐ
5. Trả lời ngắn gọn, bằng tiếng Việt"""

def run_agent(
        user_request: str, # câu hỏi từ user
        max_iterations: int = 5, # tối đa 5 vòng lặp, tránh loop vô tận
        verbose: bool = True, # True = in chi tiết ra màn hình để debug
) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}, # luật nội bộ
        {"role": "user", "content": user_request}, # câu hỏi của user
    ]

    # Lấy schema của tất cả tools để truyền cho LLM
    tool_schemas = [t["schema"] for t in TOOLS.values()]

    for iteration in range(1, max_iterations + 1):
        print(f"\n[Iteration {iteration}] LLM đang xử lý...")

        # Gửi messages + tool_schemas cho LLM
        response = ollama.chat(
            model=MODEL,
            messages=messages,
            tools=tool_schemas, # LLM biết có những tool nào
        )

        assistant_msg = response["message"]
        messages.append(dict(assistant_msg)) # lưu response vào lịch sử

        # Không có tool call → LLM đã có đủ thông tin → trả lời luôn
        if not assistant_msg.get("tool_calls"):
            answer = assistant_msg.get("content", "")
            print(f"\nAGENT: {answer}")
            print(f"✅ Xong sau {iteration} iteration(s)")
            return answer

        # Có tool call → thực thi từng tool
        for tool_call in assistant_msg["tool_calls"]:
            name = tool_call["function"]["name"] # tên tool LLM muốn gọi
            args = tool_call["function"].get("arguments", {})

            # Ollama đôi khi trả args dạng string → chuyển sang dict
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = []

            print(f"  → Gọi tool: {name}({args})")

            # Tìm tool trong Registry và chạy
            if name in TOOLS:
                result = TOOLS[name]["function"](**args)
            else:
                result = {"error": f"Tool '{name} không tồn tại"}

            print(f"  ← Kết quả: {json.dumps(result, ensure_ascii=False)}")
                
            # Trả kết quả tool về cho LLM → vòng lặp tiếp theo
            messages.append({
                "role": "tool",
                "content": json.dumps(result, ensure_ascii=False),
            })

    return "Agent đạt giới hạn iterations mà chưa hoàn thành."

if __name__ == "__main__":
    tests = [
        "Tổng doanh thu tuần này là bao nhiêu?",
        "Có bao nhiêu email đang chờ xử lý?",
        "Kiểm tra email pending rồi gửi Telegram alert.",
        "Thời tiết Hà Nội hôm nay thế nào?",
        "Báo cáo nhanh: doanh thu 7 ngày và email chờ.",
    ]

    for i, test in enumerate(tests, 1):
        print(f"\n{'#'*60}")
        print(f"TEST {i}/5")
        run_agent(test)
        input("\nEnter để tiếp tục...")