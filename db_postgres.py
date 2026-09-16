# db_postgres.py
# Tạo và seed database PostgreSQL
# Thay thế db_seed.py (SQLite) từ tuần 1
# Chạy: python db_postgres.py

import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random

load_dotenv()  # đọc .env trước khi dùng os.getenv()

# Lấy connection string từ .env
# Format: postgresql://user:password@host:port/database
POSTGRES_URL = os.getenv("POSTGRES_URL")


def get_connection():
    """
    Tạo kết nối đến PostgreSQL.
    Dùng hàm riêng để tái sử dụng ở nhiều chỗ.
    Mỗi lần gọi = 1 kết nối mới → nhớ đóng sau khi dùng.
    """
    return psycopg2.connect(POSTGRES_URL)

def create_tables():
    """
    Tạo tables trong PostgreSQL.
    Giống db_seed.py nhưng:
    - Dùng psycopg2 thay sqlite3
    - SERIAL thay AUTOINCREMENT (cú pháp PostgreSQL)
    - NUMERIC thay REAL cho tiền tệ (chính xác hơn)
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Xóa tables cũ nếu có — để re-seed sạch
    cursor.execute("DROP TABLE IF EXISTS transactions")
    cursor.execute("DROP TABLE IF EXISTS emails")

    # Tạo bảng transactions
    cursor.execute("""
        CREATE TABLE transactions (
            id            SERIAL PRIMARY KEY,
            customer_name VARCHAR(255) NOT NULL,
            amount        NUMERIC(15,2) NOT NULL,
            service       VARCHAR(255) NOT NULL,
            date          DATE NOT NULL,
            status        VARCHAR(50) NOT NULL DEFAULT 'completed'
        )
    """)
    # SERIAL = tự tăng (PostgreSQL) — SQLite dùng AUTOINCREMENT
    # NUMERIC(15,2) = số tối đa 15 chữ số, 2 số thập phân
    # → chính xác hơn REAL cho tiền tệ

    # Tạo bảng emails
    cursor.execute("""
        CREATE TABLE emails (
            id          SERIAL PRIMARY KEY,
            sender      VARCHAR(255) NOT NULL,
            subject     VARCHAR(500) NOT NULL,
            body        TEXT NOT NULL,
            received_at TIMESTAMP NOT NULL DEFAULT NOW(),
            status      VARCHAR(50) NOT NULL DEFAULT 'pending'
        )
    """)
    # TIMESTAMP = ngày + giờ (PostgreSQL)
    # DEFAULT NOW() = tự điền thời gian hiện tại

    conn.commit()
    conn.close()
    print("✅ Tables created: transactions, emails")

def seed_data():
    """
    Tạo data test trong PostgreSQL.
    Giống db_seed.py nhưng dùng psycopg2 syntax.
    """
    conn = get_connection()
    cursor = conn.cursor()

    customers = [
        "Công ty ABC Corp",
        "SME Hà Nội Phát",
        "Startup XYZ Tech",
        "Doanh nghiệp DEF",
        "Cty TNHH GHI Solutions",
    ]
    services = [
        "Scam Detection Agent",
        "Cybersecurity Audit",
        "AI Agent Setup",
        "PDPL Compliance Audit",
    ]

    # 20 transactions ngẫu nhiên
    for _ in range(20):
        days_ago = random.randint(0, 6)
        date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        cursor.execute(
            """
            INSERT INTO transactions (customer_name, amount, service, date)
            VALUES (%s, %s, %s, %s)
            """,
            # PostgreSQL dùng %s thay vì ? như SQLite
            (
                random.choice(customers),
                round(random.uniform(2_000_000, 15_000_000), 2),
                random.choice(services),
                date,
            ),
        )

    # 5 emails mẫu — có 1 scam
    emails_data = [
        ("khachhang@abc-corp.vn", "Hỏi về dịch vụ Scam Detection",
         "Chào KenTech, tôi muốn tìm hiểu về giải pháp phát hiện lừa đảo.", "pending"),
        ("scammer123@freemail.xyz", "KHẨN: Bạn đã trúng thưởng 50 triệu!",
         "Click vào link này ngay: http://fake-prize.xyz/claim", "pending"),
        ("partner@xyz-tech.com", "Đề xuất hợp tác chiến lược Q4/2026",
         "KenTech thân mến, chúng tôi muốn thảo luận về hợp tác AI Security.", "pending"),
        ("billing@aws.amazon.com", "Invoice #AWS-2026-09-001",
         "Your AWS invoice for September 2026. Amount: $127.45", "processed"),
        ("ceo@sme-vietnam.vn", "Cần tư vấn gấp về AI Security",
         "KenTech ơi, công ty tôi vừa bị tấn công phishing.", "pending"),
    ]

    for sender, subject, body, status in emails_data:
        cursor.execute(
            """
            INSERT INTO emails (sender, subject, body, status)
            VALUES (%s, %s, %s, %s)
            """,
            (sender, subject, body, status),
        )

    conn.commit()
    conn.close()
    print("✅ Data seeded: 20 transactions, 5 emails (4 pending, 1 processed)")


if __name__ == "__main__":
    print("Setting up PostgreSQL database...")
    create_tables()
    seed_data()
    print("\n✅ PostgreSQL ready — kentech_db")