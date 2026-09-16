# memory_manager.py
# Long-term memory cho agent — lưu và truy xuất conversation history
# Tuần 3: SQLite storage
# Tuần 4: Upgrade lên ChromaDB vector search

import os
import json
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Memory database riêng — không dùng chung với kentech.db
# Lý do: memory data và business data cần tách biệt
# PDPL: data khách hàng và conversation log có retention policy khác nhau
MEMORY_DB = "agent_memory.db"

def init_memory_db():
    """
    Tạo database lưu memory của agent.
    Gọi 1 lần khi khởi động — không xóa data cũ.

    2 bảng:
    - conversations: lưu từng message trong hội thoại
    - memories: lưu thông tin quan trọng được extract ra
    """
    conn = sqlite3.connect(MEMORY_DB)
    cursor = conn.cursor()

    # Bảng conversations — lưu toàn bộ lịch sử chat
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,    -- phân biệt các session khác nhau
            role       TEXT NOT NULL,    -- 'user', 'assistant', hoặc 'tool'
            content    TEXT NOT NULL,    -- nội dung message
            timestamp  TEXT NOT NULL,    -- khi nào
            tokens     INTEGER DEFAULT 0 -- ước tính số token (để quản lý size)
        )
    """)
    # CREATE TABLE IF NOT EXISTS: không báo lỗi nếu table đã tồn tại
    # Khác DROP TABLE IF EXISTS: giữ data cũ, không xóa

    # Bảng memories — lưu facts quan trọng được extract
    # Ví dụ: "ABC Corp đã nhận báo giá ngày 15/9" → lưu vào đây
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            key        TEXT NOT NULL,    -- tên/chủ đề của memory
            value      TEXT NOT NULL,    -- nội dung
            source     TEXT NOT NULL,    -- từ session nào, user nào
            confidence REAL DEFAULT 1.0, -- độ tin cậy (1.0 = chắc chắn)
            created_at TEXT NOT NULL,
            expires_at TEXT             -- NULL = không hết hạn
        )
    """)
    # confidence: quan trọng cho Memory Poisoning defense
    # Thông tin inject từ email độc hại → confidence thấp → không tin

    conn.commit()
    conn.close()
    print(f"✅ Memory DB initialized: {MEMORY_DB}")

def save_message(session_id: str, role: str, content: str) -> None:
    """
    Lưu 1 message vào conversation history.

    Gọi sau mỗi message trong agent loop:
    - User gửi request → save role='user'
    - Agent trả lời → save role='assistant'
    - Tool trả kết quả → save role='tool'

    Args:
        session_id: ID phân biệt session (dùng timestamp hoặc UUID)
        role:       'user', 'assistant', 'tool'
        content:    nội dung message
    """
    conn = sqlite3.connect(MEMORY_DB)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO conversations (session_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (
            session_id,
            role,
            content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )

    conn.commit()
    conn.close()


def load_recent_history(session_id: str, limit: int = 10) -> list:
    """
    Load N messages gần nhất của 1 session.

    Tại sao giới hạn số lượng?
    Context window của LLM có giới hạn token.
    Load quá nhiều → chậm + tốn token + có thể overflow.
    Rule of thumb: 10 messages gần nhất là đủ context.

    Args:
        session_id: ID session cần load
        limit:      số message tối đa (mặc định 10)
    Returns:
        list of dict: [{"role": ..., "content": ...}, ...]
    """
    conn = sqlite3.connect(MEMORY_DB)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT role, content
        FROM conversations
        WHERE session_id = ?
        ORDER BY timestamp DESC  -- mới nhất trước
        LIMIT ?
        """,
        (session_id, limit),
    )

    rows = cursor.fetchall()
    conn.close()

    # Đảo ngược để có thứ tự chronological (cũ → mới)
    return [
        {"role": row[0], "content": row[1]}
        for row in reversed(rows)
    ]


def save_memory(key: str, value: str, source: str, confidence: float = 1.0, expires_days: int = None) -> None:
    """
    Lưu 1 fact quan trọng vào long-term memory.

    Khác conversation history:
    - History: toàn bộ messages theo thứ tự
    - Memory: facts được extract, có thể tìm kiếm

    Ví dụ:
    save_memory(
        key="ABC Corp báo giá",
        value="Đã gửi báo giá 50M VNĐ ngày 15/9/2026",
        source="session_20260915_143200",
        confidence=1.0,
        expires_days=90  # PDPL: xóa sau 90 ngày
    )

    Args:
        key:          tên/chủ đề để tìm kiếm sau
        value:        nội dung fact
        source:       nguồn gốc (session ID)
        confidence:   độ tin cậy 0.0-1.0
        expires_days: số ngày trước khi hết hạn (PDPL compliance)
    """
    conn = sqlite3.connect(MEMORY_DB)
    cursor = conn.cursor()

    expires_at = None
    if expires_days:
        from datetime import timedelta
        expires_at = (datetime.now() + timedelta(days=expires_days)).strftime("%Y-%m-%d")

    cursor.execute(
        """
        INSERT INTO memories (key, value, source, confidence, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            key,
            value,
            source,
            confidence,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            expires_at,
        ),
    )

    conn.commit()
    conn.close()


def search_memory(query: str, min_confidence: float = 0.7) -> list:
    """
    Tìm kiếm trong long-term memory.

    Tuần 3: simple text search (LIKE)
    Tuần 4: upgrade lên semantic search với ChromaDB

    min_confidence: chỉ lấy memory có độ tin cậy >= ngưỡng này
    → Defense đầu tiên chống Memory Poisoning:
      Memory bị inject có confidence thấp → bị lọc ra
    """
    conn = sqlite3.connect(MEMORY_DB)
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        """
        SELECT key, value, source, confidence, created_at
        FROM memories
        WHERE (key LIKE ? OR value LIKE ?)
          AND confidence >= ?
          AND (expires_at IS NULL OR expires_at > ?)
        ORDER BY confidence DESC, created_at DESC
        """,
        (f"%{query}%", f"%{query}%", min_confidence, now),
    )

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "key":        row[0],
            "value":      row[1],
            "source":     row[2],
            "confidence": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]

if __name__ == "__main__":
    print("Testing Memory Manager...")
    print()

    # Khởi tạo DB
    init_memory_db()

    # ── Test 1: Lưu conversation history ──────────────────
    print("Test 1: Save conversation history")
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    save_message(session_id, "user", "Báo giá cho ABC Corp bao nhiêu?")
    save_message(session_id, "assistant", "Đã gửi báo giá 50 triệu VNĐ cho ABC Corp lúc 14:32.")
    save_message(session_id, "user", "ABC Corp có reply chưa?")
    save_message(session_id, "assistant", "Chưa thấy reply từ ABC Corp.")

    print(f"✅ Saved 4 messages for session: {session_id}")

    # ── Test 2: Load history ───────────────────────────────
    print("\nTest 2: Load recent history")
    history = load_recent_history(session_id, limit=10)
    for msg in history:
        print(f"  [{msg['role']}]: {msg['content'][:50]}...")

    # ── Test 3: Lưu long-term memory ──────────────────────
    print("\nTest 3: Save long-term memory")
    save_memory(
        key="ABC Corp báo giá",
        value="Đã gửi báo giá 50 triệu VNĐ ngày 15/9/2026. Chưa có reply.",
        source=session_id,
        confidence=1.0,
        expires_days=90   # PDPL: xóa sau 90 ngày
    )
    save_memory(
        key="scammer123 email scam",
        value="Email từ scammer123@freemail.xyz là scam — 'trúng thưởng 50 triệu'",
        source=session_id,
        confidence=1.0,
        expires_days=365  # giữ lâu hơn để reference sau
    )
    print("✅ Saved 2 memories")

    # ── Test 4: Search memory ──────────────────────────────
    print("\nTest 4: Search memory")
    results = search_memory("ABC Corp")
    for r in results:
        print(f"  [{r['confidence']}] {r['key']}: {r['value'][:60]}...")

    # ── Test 5: Search với confidence filter ──────────────
    print("\nTest 5: Low confidence memory bị filter")
    save_memory(
        key="fake info",
        value="Đây là thông tin giả được inject",
        source="unknown_source",
        confidence=0.3,   # thấp — giả lập memory bị poison
        expires_days=30
    )
    results_high = search_memory("fake", min_confidence=0.7)
    results_low  = search_memory("fake", min_confidence=0.0)
    print(f"  min_confidence=0.7: {len(results_high)} kết quả (filtered out)")
    print(f"  min_confidence=0.0: {len(results_low)} kết quả (bao gồm poisoned)")

    print("\n✅ Memory Manager working!")