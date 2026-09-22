"""데이터베이스 연결 및 CRUD 함수"""

import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv
from config import cfg

# DB는 도구 전체에서 하나만 사용하고, 항상 프로젝트 저장소 루트에 둔다.
# 예전 DB_PATH 환경변수는 호환성을 위해 읽을 수 있지만 위치를 바꾸지는 않는다.
load_dotenv(os.path.join(cfg.PROGRAM_DIR, ".env"))
DB_PATH = cfg.DATABASE_PATH
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_connection():
    """DB 연결 객체 반환"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # dict처럼 접근 가능
    return conn


def init_database():
    """테이블 생성 (앱 시작 시 한 번 실행)"""
    conn = get_connection()
    cursor = conn.cursor()

    # 리뷰 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            game_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 분석결과 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER UNIQUE,
            sentiment TEXT,
            keywords TEXT,
            confidence REAL,
            analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (review_id) REFERENCES reviews(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("[OK] 데이터베이스 초기화 완료")


# === 리뷰 CRUD ===

def create_review(content: str, game_name: str = None) -> int:
    """리뷰 저장, 생성된 ID 반환"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reviews (content, game_name) VALUES (?, ?)",
        (content, game_name)
    )
    review_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return review_id


def get_review(review_id: int) -> dict:
    """ID로 리뷰 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reviews WHERE id = ?", (review_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_reviews() -> list:
    """모든 리뷰 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reviews ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# === 분석결과 CRUD ===

def save_analysis(review_id: int, sentiment: str, keywords: list, confidence: float):
    """분석결과 저장"""
    conn = get_connection()
    cursor = conn.cursor()
    keywords_str = ",".join(keywords)
    cursor.execute('''
        INSERT OR REPLACE INTO analysis_results
        (review_id, sentiment, keywords, confidence, analyzed_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (review_id, sentiment, keywords_str, confidence, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_analysis(review_id: int) -> dict:
    """리뷰 ID로 분석결과 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM analysis_results WHERE review_id = ?", (review_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        result = dict(row)
        result["keywords"] = result["keywords"].split(",") if result["keywords"] else []
        return result
    return None


def get_stats() -> dict:
    """통계 계산"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM reviews")
    total_reviews = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM analysis_results")
    analyzed_count = cursor.fetchone()[0]
    cursor.execute('''
        SELECT sentiment, COUNT(*) as count
        FROM analysis_results GROUP BY sentiment
    ''')
    sentiment_rows = cursor.fetchall()
    sentiment_distribution = {row["sentiment"]: row["count"] for row in sentiment_rows}
    conn.close()
    return {
        "total_reviews": total_reviews,
        "analyzed_count": analyzed_count,
        "sentiment_distribution": sentiment_distribution
    }
