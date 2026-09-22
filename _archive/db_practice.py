"""37차시 DB 구축 실습 스크립트 (session 39 노트북 → .py 변환)

실행: python db_practice.py
산출물: review_analysis_practice.db
       - reviews 테이블 (id, game_id, content, author, playtime_hours, recommended, created_at)
       - analysis_results 테이블 (id, review_id, sentiment, keywords, summary, analyzed_at)
       - 다양한 SELECT 쿼리 결과 출력

※ session 40 메인 API와 충돌하지 않도록 별도 DB 파일(review_analysis_practice.db)을 사용합니다.
"""

import sqlite3
import os

DB_FILE = "review_analysis_practice.db"

# 이전 실행본 정리(반복 실행해도 동일 결과 보장)
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

# ===== Step 1: DB 연결 =====
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
print(f"✅ {DB_FILE} 연결 완료!\n")


# ===== Step 2: reviews 테이블 생성 =====
cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id TEXT NOT NULL,
        content TEXT NOT NULL,
        author TEXT,
        playtime_hours INTEGER DEFAULT 0,
        recommended INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()
print("✅ reviews 테이블 생성 완료!")


# ===== Step 3: analysis_results 테이블 생성 (FOREIGN KEY) =====
cursor.execute('''
    CREATE TABLE IF NOT EXISTS analysis_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_id INTEGER NOT NULL,
        sentiment TEXT,
        keywords TEXT,
        summary TEXT,
        analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (review_id) REFERENCES reviews (id)
    )
''')
conn.commit()
print("✅ analysis_results 테이블 생성 완료!\n")


# ===== Step 4: 샘플 리뷰 데이터 삽입 (INSERT) =====
sample_reviews = [
    ('game_001', '정말 재밌는 게임이에요! 스토리도 좋고 그래픽도 최고!', 'Player123', 120, 1),
    ('game_001', '버그가 너무 많아요. 진행이 안 됩니다.', 'GamerX', 5, 0),
    ('game_001', '그냥 그래요. 할만하긴 한데 특별한 건 없어요.', 'CasualGamer', 30, 1),
    ('game_001', '최고의 게임! 100시간 넘게 플레이했어요.', 'ProGamer99', 150, 1),
    ('game_001', '환불하고 싶어요. 돈 아까워요.', 'AngryUser', 2, 0),
    ('game_002', '전작보다 훨씬 나아졌어요!', 'SeriesFan', 80, 1),
    ('game_002', '아직 최적화가 부족해요. 프레임이 끊겨요.', 'TechUser', 10, 0),
    ('game_002', '멀티플레이가 재밌어요! 친구랑 같이 하세요.', 'CoopPlayer', 60, 1),
]
cursor.executemany('''
    INSERT INTO reviews (game_id, content, author, playtime_hours, recommended)
    VALUES (?, ?, ?, ?, ?)
''', sample_reviews)
conn.commit()
print(f"✅ {len(sample_reviews)}개 리뷰 삽입 완료!")


# ===== Step 5: 샘플 분석 결과 삽입 =====
sample_analysis = [
    (1, '긍정', '스토리,그래픽,재미', '스토리와 그래픽을 극찬하는 긍정적 리뷰'),
    (2, '부정', '버그,진행불가', '버그로 인한 게임 진행 불가 불만'),
    (3, '중립', '평범,무난', '특별한 장단점 없이 평범하다는 평가'),
    (4, '긍정', '최고,장시간', '장시간 플레이할 만큼 재미있다는 극찬'),
    (5, '부정', '환불,후회', '구매를 후회하는 강한 부정적 리뷰'),
    (6, '긍정', '개선,전작', '전작 대비 개선점을 평가하는 긍정적 리뷰'),
    (7, '부정', '최적화,프레임', '기술적 문제에 대한 불만'),
    (8, '긍정', '멀티플레이,친구,협동', '협동 플레이를 추천하는 긍정적 리뷰'),
]
cursor.executemany('''
    INSERT INTO analysis_results (review_id, sentiment, keywords, summary)
    VALUES (?, ?, ?, ?)
''', sample_analysis)
conn.commit()
print(f"✅ {len(sample_analysis)}개 분석 결과 삽입 완료!\n")


# ===== Step 6: 데이터 조회 (SELECT) =====
print("=" * 50)
print("=== 전체 리뷰 목록 (SELECT *) ===")
print("=" * 50)
cursor.execute('SELECT id, content, author, recommended FROM reviews')
for row in cursor.fetchall():
    rec = "👍 추천" if row[3] == 1 else "👎 비추천"
    print(f"[{row[0]}] {row[2]}: {row[1][:30]}... {rec}")

print("\n=== 추천 리뷰만 (WHERE) ===")
cursor.execute('SELECT content, author FROM reviews WHERE recommended = 1')
for row in cursor.fetchall():
    print(f"{row[1]}: {row[0][:40]}...")

print("\n=== 게임별 리뷰 수 집계 (GROUP BY) ===")
cursor.execute('''
    SELECT game_id, COUNT(*) as review_count,
           SUM(CASE WHEN recommended = 1 THEN 1 ELSE 0 END) as positive_count
    FROM reviews
    GROUP BY game_id
''')
for row in cursor.fetchall():
    pct = (row[2] / row[1]) * 100 if row[1] > 0 else 0
    print(f"{row[0]}: 총 {row[1]}개 리뷰 (추천률: {pct:.0f}%)")

print("\n=== 감성별 분석 결과 (GROUP BY) ===")
cursor.execute('''
    SELECT sentiment, COUNT(*) as count
    FROM analysis_results
    GROUP BY sentiment
''')
for row in cursor.fetchall():
    emoji = {"긍정": "😊", "부정": "😠", "중립": "😐"}.get(row[0], "")
    print(f"{emoji} {row[0]}: {row[1]}개")

print("\n=== 리뷰 + 분석 결과 함께 (JOIN) ===")
cursor.execute('''
    SELECT r.content, a.sentiment, a.keywords
    FROM reviews r
    JOIN analysis_results a ON r.id = a.review_id
''')
for row in cursor.fetchall():
    print(f"[{row[1]}] {row[0][:25]}... | 키워드: {row[2]}")


# ===== Step 7: 데이터 수정 (UPDATE) =====
print("\n=== 데이터 수정 (UPDATE) ===")
cursor.execute('''
    UPDATE analysis_results
    SET sentiment = '긍정'
    WHERE review_id = 3
''')
conn.commit()
cursor.execute('SELECT * FROM analysis_results WHERE review_id = 3')
print(f"수정된 분석 결과: {cursor.fetchone()}")


# ===== Step 8: 테이블 구조 확인 (PRAGMA) =====
print("\n=== 생성된 테이블 목록 ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
for table in cursor.fetchall():
    print(f"📋 {table[0]}")

print("\n=== reviews 테이블 구조 ===")
cursor.execute("PRAGMA table_info(reviews)")
for col in cursor.fetchall():
    print(f"  {col[1]:15} | {col[2]:10} | {'NOT NULL' if col[3] else 'NULL OK'}")

print("\n=== analysis_results 테이블 구조 ===")
cursor.execute("PRAGMA table_info(analysis_results)")
for col in cursor.fetchall():
    print(f"  {col[1]:15} | {col[2]:10} | {'NOT NULL' if col[3] else 'NULL OK'}")


# ===== Step 9: 연결 종료 =====
conn.close()
print("\n✅ 데이터베이스 연결 종료!")
print(f"📁 산출물: {DB_FILE}")
