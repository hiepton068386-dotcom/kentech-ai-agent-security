import sqlite3
from datetime import datetime, timedelta
import random

def seed_database():
    conn = sqlite3.connect("kentech.db")
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS transactions")
    cursor.execute("DROP TABLE IF EXISTS emails")

    cursor.execute("""
        CREATE TABLE transactions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT  NOT NULL,
            amount        REAL  NOT NULL,
            service       TEXT  NOT NULL, 
            date          TEXT  NOT NULL, 
            status        TEXT  NOT NULL DEFAULT 'completed'
        )
    """)

    cursor.execute("""
        CREATE TABLE emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            sender TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            received_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )
    """)

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

    for _ in range(20):
        days_ago = random.randint(0, 6)
        date = (datetime.now() - timedelta(days=days_ago)).strftime("%y-%m-%d")
        cursor.execute(
            "INSERT INTO transactions (customer_name, amount, service, date) VALUES (?, ?, ?, ?)",
            (
                random.choice(customers),
                round(random.uniform(2_000_000, 15_000_000), 0),
                random.choice(services),
                date,
            ),
        )

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

    now = datetime.now().strftime("%y-%m-%d %H:%M")
    for sender, subject, body, status in emails_data:
        cursor.execute(
            "INSERT INTO emails (sender, subject, body, received_at, status) VALUES (?, ?, ?, ?, ?)",
            (sender, subject, body, now, status),
        )

    conn.commit()
    conn.close()
    print("✅ kentech.db created")
    print("   Transactions: 20 rows")
    print("   Emails: 5 rows (4 pending, 1 processed)")

if __name__ == "__main__":
    seed_database()