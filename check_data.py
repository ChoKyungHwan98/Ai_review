import json
from config import cfg

APP_ID = 1627720
with open(cfg.project_file('insights_v4.json', APP_ID), 'r', encoding='utf-8') as f:
    ins = json.load(f)

print('=== TOP LEVEL KEYS ===')
for k in ins.keys():
    v = ins[k]
    if isinstance(v, list):
        print(f'{k}: list({len(v)})')
    elif isinstance(v, dict):
        print(f'{k}: dict(keys={list(v.keys())[:6]})')
    else:
        print(f'{k}: {str(v)[:80]}')

print('\n=== aspect_evidence ===')
ev = ins.get('aspect_evidence', {})
for asp, data in ev.items():
    neg = data.get('negative', [])
    pos = data.get('positive', [])
    print(f'{asp}: neg={len(neg)}건, pos={len(pos)}건')
    if neg:
        print(f'  부정예: {neg[0][:60]}')

print('\n=== aspect_priority ===')
for p in ins.get('aspect_priority', []):
    kr = p.get('aspect_kr', p.get('aspect', ''))
    neg = p.get('neg_rate', 0)
    pos = p.get('pos_rate', 0)
    n = p.get('n', 0)
    print(f'{kr}: neg={neg:.0f}%, pos={pos:.0f}%, n={n}건')

print('\n=== top_phrases_neg sample ===')
for phr in ins.get('top_phrases_neg', [])[:5]:
    print(f'  {phr}')

print('\n=== top_phrases_pos sample ===')
for phr in ins.get('top_phrases_pos', [])[:5]:
    print(f'  {phr}')
