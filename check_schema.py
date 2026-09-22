import json, os
from config import cfg

for folder in ['1623730', '1627720', '730']:
    path = cfg.project_file('insights_v4.json', int(folder))
    if not os.path.exists(path):
        print(f'{folder}: 파일 없음')
        continue
    with open(path, 'r', encoding='utf-8') as f:
        ins = json.load(f)

    game = ins.get('game_name', folder)
    print(f'=== {folder} ({game}) ===')

    # (1) priority 경로
    pri1 = ins.get('aspects', {}).get('priority', [])
    pri2 = ins.get('aspect_priority', [])
    print(f'  aspects.priority: {len(pri1)}개  /  aspect_priority(root): {len(pri2)}개')

    # (2) priority 필드명
    pri = pri1 if pri1 else pri2
    if pri:
        p0 = pri[0]
        print(f'  priority[0] keys: {list(p0.keys())}')
        # neg_rate_s 존재 여부
        if 'neg_rate_s' in p0:
            print(f'  -> neg_rate_s 필드 있음 ({p0["neg_rate_s"]:.1f}%)')
        elif 'neg_rate' in p0:
            print(f'  -> neg_rate 필드 있음 ({p0["neg_rate"]:.1f}%) [구버전]')
        else:
            print(f'  -> 부정률 필드 없음 !')

        if 'mentioned_s' in p0:
            print(f'  -> mentioned_s 필드 있음 ({p0["mentioned_s"]}건)')
        elif 'mentioned' in p0:
            print(f'  -> mentioned 필드 있음 ({p0["mentioned"]}건) [구버전]')
        else:
            print(f'  -> mentioned 필드 없음 !')

    # (3) emotion 구조
    emo = ins.get('emotion', {})
    print(f'  emotion keys: {list(emo.keys())}')
    joy = emo.get('JOY', {})
    if joy:
        print(f'  JOY sub-keys: {list(joy.keys())}')
    
    # (4) evidence
    ev = ins.get('aspect_evidence', {})
    print(f'  evidence aspects: {list(ev.keys())}')
    if ev:
        first_key = list(ev.keys())[0]
        first_val = ev[first_key]
        print(f'  evidence[{first_key}] keys: {list(first_val.keys())}')
    print()
