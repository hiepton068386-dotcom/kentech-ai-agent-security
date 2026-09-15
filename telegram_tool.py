# telegram_tool.py
# Telegram Bot API thật — thay thế mock của tuần 1
# Chạy: python telegram_tool.py

import os                           # đọc environment variables
import requests                     # gọi HTTP API (Telegram dùng REST API)
from dotenv import load_dotenv      # đọc file .env

# Đọc file .env vào environment
# Sau dòng này, os.getenv() mới đọc được biến từ .env
load_dotenv()

# Lấy credentials từ .env — KHÔNG hardcode trực tiếp
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message: str, priority: str = "normal") -> dict:
    """
    Gửi message thật qua Telegram Bot API.

    Khác với mock tuần 1:
    - Tuần 1: chỉ print ra terminal
    - Tuần 2: gọi API thật → message đến điện thoại

    Args:
        message:  nội dung tin nhắn
        priority: low/normal/high/critical → hiển thị emoji khác nhau
    Returns:
        dict với status và response từ Telegram API
    """
    # Emoji theo priority — giúp chị Lan nhận ra mức độ khẩn cấp
    emoji = {
        "low":      "ℹ️",
        "normal":   "📢",
        "high":     "⚠️",
        "critical": "🚨"
    }.get(priority, "📢")

    # Format message với emoji + priority label
    formatted = f"{emoji} [{priority.upper()}] {message}"

    # Telegram Bot API endpoint
    # Mỗi action là 1 URL khác nhau:
    # sendMessage, sendPhoto, deleteMessage...
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # Payload gửi đến Telegram
    payload = {
        "chat_id": CHAT_ID,    # gửi đến ai
        "text":    formatted,  # nội dung
        "parse_mode": "HTML"   # cho phép dùng <b>bold</b> trong message
    }

    try:
        # Gọi Telegram API
        response = requests.post(
            url,
            json=payload,    # json= tự động set Content-Type: application/json
            timeout=10       # timeout 10 giây — không chờ mãi nếu mạng chậm
        )

        # Kiểm tra HTTP status code
        # 200 = OK, 4xx = lỗi client, 5xx = lỗi server
        response.raise_for_status()

        result = response.json()  # parse JSON response từ Telegram

        if result.get("ok"):
            print(f"✅ Telegram: '{formatted}'")
            return {"status": "sent", "message": formatted}
        else:
            print(f"❌ Telegram API error: {result}")
            return {"status": "failed", "error": result}

    except requests.exceptions.Timeout:
        # Mạng chậm hoặc Telegram down
        print("❌ Timeout: Telegram không phản hồi trong 10 giây")
        return {"status": "failed", "error": "timeout"}

    except requests.exceptions.RequestException as e:
        # Mọi lỗi network khác
        print(f"❌ Network error: {e}")
        return {"status": "failed", "error": str(e)}

if __name__ == "__main__":
    print("Testing Telegram Bot API...")
    print(f"Bot Token: {BOT_TOKEN[:10]}...")  # chỉ in 10 ký tự đầu — bảo mật
    print(f"Chat ID: {CHAT_ID}")
    print()

    # Test 1: Message bình thường
    send_telegram_message(
        "KenTech Agent đang online. Tuần 2 bắt đầu!",
        priority="normal"
    )

    # Test 2: Critical alert — giả lập phát hiện scam
    send_telegram_message(
        "🚨 PHÁT HIỆN EMAIL SCAM từ scammer123@freemail.xyz — ĐỪNG CHUYỂN KHOẢN!",
        priority="critical"
    )