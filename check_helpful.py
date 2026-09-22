import csv
from config import cfg

APP_ID = 1627720
with open(cfg.project_file('reviews.csv', APP_ID), 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# votes_up 기준 상위 10개
sorted_rows = sorted(rows, key=lambda r: int(r.get('votes_up', 0) or 0), reverse=True)

with open(cfg.project_file('helpful_top.txt', APP_ID), 'w', encoding='utf-8') as out:
    out.write(f"총 리뷰: {len(rows)}건\n\n")
    out.write("=== votes_up 상위 10개 ===\n\n")
    for i, r in enumerate(sorted_rows[:10]):
        voted = "긍정" if r.get('voted_up','').lower() == 'true' else "부정"
        votes = r.get('votes_up', '0')
        ws = r.get('weighted_vote_score', '?')
        pt = int(r.get('playtime_forever_min', 0) or 0) // 60
        review = r.get('content', r.get('review', ''))[:300].replace('\n',' ')
        out.write(f"[{i+1}] votes_up={votes} | weighted={ws} | {voted} | 플레이타임:{pt}h\n")
        out.write(f"  {review}\n\n")

    # 분포
    out.write("=== votes_up 분포 ===\n")
    zero = sum(1 for r in rows if int(r.get('votes_up',0) or 0) == 0)
    one_plus = sum(1 for r in rows if int(r.get('votes_up',0) or 0) >= 1)
    ten_plus = sum(1 for r in rows if int(r.get('votes_up',0) or 0) >= 10)
    fifty_plus = sum(1 for r in rows if int(r.get('votes_up',0) or 0) >= 50)
    out.write(f"  votes=0: {zero}건 ({zero/len(rows)*100:.1f}%)\n")
    out.write(f"  votes>=1: {one_plus}건 ({one_plus/len(rows)*100:.1f}%)\n")
    out.write(f"  votes>=10: {ten_plus}건 ({ten_plus/len(rows)*100:.1f}%)\n")
    out.write(f"  votes>=50: {fifty_plus}건 ({fifty_plus/len(rows)*100:.1f}%)\n")

print("done")
