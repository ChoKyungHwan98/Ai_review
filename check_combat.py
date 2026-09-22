import json, csv
from config import cfg

APP_ID = 1627720
with open(cfg.project_file('insights_v4.json', APP_ID), 'r', encoding='utf-8') as f:
    ins = json.load(f)

# gameplay 원문
ev = ins.get('aspect_evidence', {})
gp = ev.get('gameplay', {})
with open(cfg.project_file('combat_result.txt', APP_ID), 'w', encoding='utf-8') as out:
    out.write("=== gameplay 원문 ===\n")
    out.write("긍정:\n")
    for q in gp.get('positive', []):
        out.write(f"  + {q}\n")
    out.write("부정:\n")
    for q in gp.get('negative', []):
        out.write(f"  - {q}\n")

    keywords = ['전투', '공격', '회피', '구르기', '패링', '보스', '타격감', '액션', '스태미나', '무기', '칼']
    with open(cfg.project_file('analysis_v2.csv', APP_ID), 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    out.write(f"\n총 리뷰: {len(rows)}건\n\n")
    for kw in keywords:
        matches = [r for r in rows if kw in r.get('review', '')]
        if matches:
            voted_up = sum(1 for r in matches if r.get('voted_up','').lower()=='true')
            out.write(f"[{kw}] {len(matches)}건 (긍정:{voted_up} 부정:{len(matches)-voted_up})\n")
            for r in matches[:2]:
                txt = r.get('review', '')[:80].replace('\n',' ')
                v = 'pos' if r.get('voted_up','').lower()=='true' else 'neg'
                out.write(f"  [{v}] {txt}\n")
            out.write("\n")
        else:
            out.write(f"[{kw}] 0건\n")

print("Done")
