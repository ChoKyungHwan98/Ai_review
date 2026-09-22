import httpx
import json

app_id = '1627720'
r = httpx.get(f'http://127.0.0.1:8765/dashboard/data/v4?app_id={app_id}')
data = r.json()

lines = []
lines.append(f"# {data.get('game_name', 'P의 거짓')} - 종합 리뷰 분석 데이터 (대시보드 전체 요약)")
lines.append("")

# 1. 샘플링 및 신뢰도
lines.append("## 1. 샘플링 설계 및 신뢰도 (Data Reliability)")
pop = data.get('population', {})
s_design = data.get('sample_design', {})
lines.append(f"* **모집단 (전체 한국어 리뷰)**: {pop.get('total', 0):,}건 (긍정 {pop.get('pos_rate', 0)*100:.1f}%)")
lines.append(f"* **분석 표본**: {data.get('n_total', 0):,}건")
if 'error_pct' in s_design:
    lines.append(f"* **표본 오차율**: {s_design.get('error_pct'):.1f}% (신뢰수준 95%)")

b_audit = data.get('bias_audit', {})
lines.append(f"* **통계 보정 (Bias Correction)**: 모집단 추천률({b_audit.get('population_voted_pos_pct', 0):.1f}%)과 표본 추천률({b_audit.get('sample_voted_pos_pct', 0):.1f}%) 간 오차 {b_audit.get('bias_pp', 0):.1f}%p. 추천/비추천 가중치 부여를 통해 실제 시장 반응으로 보정 완료.")
lines.append("")

# 2. 플레이타임 구간별 분석
lines.append("## 2. 플레이타임 구간별 긍정 평가율 (Playtime Analysis)")
pt = data.get('playtime', {})
for k, v in pt.items():
    if not v: continue
    total = v.get('pos', 0) + v.get('neg', 0)
    rate = v.get('pos', 0) / total * 100 if total > 0 else 0
    lines.append(f"* **{k}**: 긍정률 {rate:.1f}% (총 {total}건: 긍정 {v.get('pos', 0)}, 부정 {v.get('neg', 0)})")
lines.append("")

# 3. 감정 및 정서 분포
lines.append("## 3. 정서 분포 (Emotion & Sentiment)")
s_weight = data.get('sentiment_weighted', {})
total_s = sum(s_weight.values())
if total_s > 0:
    lines.append("**[긍/부정 (Sentiment)]**")
    for k, v in s_weight.items():
        lines.append(f"* {k}: {v/total_s*100:.1f}%")
    lines.append("")

e_weight = data.get('emotion_weighted', {})
total_e = sum(e_weight.values())
if total_e > 0:
    lines.append("**[세부 감정 (Emotion)]**")
    lines.append(f"* 기쁨 (JOY): {e_weight.get('JOY', 0)/total_e*100:.1f}%")
    lines.append(f"* 만족 (SATISFACTION): {e_weight.get('SATISFACTION', 0)/total_e*100:.1f}%")
    lines.append(f"* 분노 (ANGER): {e_weight.get('ANGER', 0)/total_e*100:.1f}%")
    lines.append(f"* 실망 (DISAPPOINTMENT): {e_weight.get('DISAPPOINTMENT', 0)/total_e*100:.1f}%")
    lines.append(f"* 중립/기타: {(e_weight.get('NEUTRAL', 0)+e_weight.get('BOREDOM', 0)+e_weight.get('SURPRISE', 0))/total_e*100:.1f}%")
    lines.append("")

# 4. 분야별 우선순위 및 현황
lines.append("## 4. 기획 요소별 긍부정 현황 (Aspect Priority)")
lines.append("분석된 리뷰에서 각 기획 요소(전투, 스토리 등)가 얼마나 언급되었는지, 그리고 그에 대한 반응은 어떠한지 보여줍니다.")
for p in data.get('priority', []):
    lines.append(f"* **{p.get('aspect_kr', '')}** (언급량: {p.get('mentioned_s', 0)}건)")
    lines.append(f"  - 긍정: {p.get('pos_s', 0)}건 / 부정: {p.get('neg_s', 0)}건 (부정률: {p.get('neg_rate_s', 0):.1f}%)")
lines.append("")

# 5. 자주 언급된 핵심 키워드
lines.append("## 5. 유저 자주 언급 키워드 (Top Phrases)")
lines.append("**[긍정 키워드 TOP 5]**")
for phrase in data.get('top_phrases_pos', [])[:5]:
    lines.append(f"* {phrase[0]} (빈도: {phrase[1]})")
lines.append("")
lines.append("**[부정 키워드 TOP 5]**")
for phrase in data.get('top_phrases_neg', [])[:5]:
    lines.append(f"* {phrase[0]} (빈도: {phrase[1]})")
lines.append("")

# 6. LLM 기획 인사이트 (가설 및 제안)
lines.append("## 6. AI 리뷰 기반 기획 인사이트 (Hypothesis & Design Proposals)")
llm_hypo = data.get('llm_hypothesis', {})
if 'hypotheses' in llm_hypo:
    for idx, h in enumerate(llm_hypo['hypotheses']):
        lines.append(f"### 가설 {idx+1}. {h.get('category')}")
        lines.append(f"* **이슈 요약**: {h.get('issue')}")
        lines.append(f"* **원인 가설**: {h.get('hypothesis')}")
        lines.append(f"* **기획 제안**: {h.get('design_proposal')}")
        lines.append("")

# 7. AI 분석 요약
lines.append("## 7. 종합 AI 분석 요약 (Executive Summary)")
insights = data.get('llm_insights', {})
if 'key_findings' in insights:
    for f in insights['key_findings']:
        lines.append(f"* **{f.get('type')}**: {f.get('finding')}")
lines.append("")
if 'recommendations' in insights:
    lines.append("**[핵심 조치 권고]**")
    for r in insights['recommendations']:
        lines.append(f"{r.get('priority')}. **{r.get('action')}**: {r.get('reason')}")

output = '\n'.join(lines)
output_path = r'c:\Users\Admin\Desktop\게임기획\포트폴리오\P의거짓_대시보드_풀데이터_Claude용.md'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(output)
print(f'완료: {output_path}')
