/* 리뷰 원문 · 수집 설계 화면. 데이터는 /dashboard/data/v5 응답(DATA)만 쓴다. */
window.ReviewPages = (() => {
  const LANG_NAMES = {koreana:'한국어', english:'영어', japanese:'일본어', schinese:'중국어 간체', tchinese:'중국어 번체', russian:'러시아어', spanish:'스페인어', latam:'스페인어(중남미)', brazilian:'포르투갈어(브라질)', german:'독일어', french:'프랑스어', polish:'폴란드어', turkish:'튀르키예어', thai:'태국어', vietnamese:'베트남어', all:'모든 언어', unknown:'언어 미상'};
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = x => x == null || x === '' ? '—' : Number(x).toLocaleString('ko-KR');
  const pct = x => x == null ? '—' : `${Number(x).toFixed(1)}%`;
  const MOODS = [
    {key:'POSITIVE', label:'긍정', cls:'pos'},
    {key:'MIXED', label:'혼합', cls:'mix'},
    {key:'NEGATIVE', label:'부정', cls:'neg'},
    {key:'NEUTRAL', label:'판단 어려움', cls:'unk'}];
  const PAGE = 40;

  /* ---------------- 리뷰 원문 ---------------- */
  let rows = [], topics = [], filter, shown, root;

  const topicsOf = r => String(r.keywords || '').split('|').map(k => k.split('@')[0].trim()).filter(Boolean);
  const moodOf = r => MOODS.some(m => m.key === r.overall_sentiment) ? r.overall_sentiment : 'NEUTRAL';
  const isUp = r => !['0', 'false', 'False'].includes(String(r.voted_up));

  function renderReviews(data) {
    root = document.getElementById('rpReviews');
    if (!root) return;
    rows = (data?.reviews || []).map(r => ({...r, _topics: topicsOf(r), _mood: moodOf(r), _up: isUp(r)}));
    const themes = data?.evidence?.themes || [];
    topics = [...themes].sort((a, b) => b.mentions - a.mentions).slice(0, 14);
    filter = {mood: '', vote: '', topic: '', q: ''};
    shown = PAGE;
    if (!rows.length) { root.innerHTML = '<div class="rp-card rp-empty">분석된 리뷰가 아직 없습니다.</div>'; return; }
    root.innerHTML = `
      <div class="rp-card rp-filters">
        <div class="rp-filter-row">
          <span class="rp-label">AI가 본 반응</span>
          <div class="rp-mood-bar" id="rpMoodBar"></div>
          <div class="rp-mood-key" id="rpMoodKey" aria-label="반응별 리뷰 선택"></div>
        </div>
        <div class="rp-filter-row rp-filter-controls">
          <span class="rp-label">Steam 평가</span>
          <div class="rp-toggle" id="rpVote"><button data-vote="">전체</button><button data-vote="up">추천</button><button data-vote="down">비추천</button></div>
          <input class="rp-search" id="rpSearch" type="search" placeholder="리뷰 내용 검색" aria-label="리뷰 내용 검색" />
        </div>
        <details class="rp-topic-disclosure" id="rpTopicDisclosure" ${topics.length ? '' : 'hidden'}>
          <summary>주제 필터 <span id="rpTopicSummary"></span></summary>
          <div class="rp-chips" id="rpTopics"></div>
        </details>
      </div>
      <div class="rp-result-head"><span id="rpCount"></span><button class="rp-text-btn" id="rpReset">필터 초기화</button></div>
      <div class="rp-list" id="rpList"></div>`;
    root.onclick = onReviewsClick;
    document.getElementById('rpSearch').addEventListener('input', e => { filter.q = e.target.value.trim().toLowerCase(); shown = PAGE; draw(); });
    draw();
  }

  function matches(r, skip) {
    if (skip !== 'mood' && filter.mood && r._mood !== filter.mood) return false;
    if (skip !== 'vote' && filter.vote && (filter.vote === 'up') !== r._up) return false;
    if (skip !== 'topic' && filter.topic && !r._topics.includes(filter.topic)) return false;
    if (filter.q && !`${r.content} ${r.key_phrase || ''}`.toLowerCase().includes(filter.q)) return false;
    return true;
  }

  function draw() {
    // 반응 막대: 다른 필터를 적용한 뒤의 구성. 누르면 그 반응만 본다.
    const base = rows.filter(r => matches(r, 'mood'));
    const total = base.length || 1;
    document.getElementById('rpMoodBar').innerHTML = MOODS.map(m => {
      const n = base.filter(r => r._mood === m.key).length;
      if (!n) return '';
      const w = n / total * 100;
      const label = w >= 9 ? `${m.label} ${Math.round(w)}%` : '';
      return `<button class="rp-seg ${m.cls} ${filter.mood && filter.mood !== m.key ? 'is-dim' : ''}" data-mood="${m.key}" style="flex:${w} 1 0" aria-pressed="${filter.mood === m.key}" aria-label="${m.label} ${num(n)}건 (${pct(w)})" title="${m.label} ${num(n)}건 (${pct(w)})"><span>${label}</span></button>`;
    }).join('');
    document.getElementById('rpMoodKey').innerHTML = MOODS.map(m => {
      const n = base.filter(r => r._mood === m.key).length;
      if (!n) return '';
      return `<button class="rp-mood-item ${m.cls}" data-mood="${m.key}" aria-pressed="${filter.mood === m.key}" aria-label="${m.label} ${num(n)}건 (${pct(n / total * 100)})">${m.label} <b>${Math.round(n / total * 100)}%</b></button>`;
    }).join('');
    // 주제는 이름으로 고른다. 불만 비율은 진단 차트에서 확인한다.
    document.getElementById('rpTopics').innerHTML = topics.map(t => {
      return `<button class="rp-chip" data-topic="${esc(t.name)}" aria-pressed="${filter.topic === t.name}" title="${esc(t.name)} · 칭찬 ${num(t.pos)} · 불만 ${num(t.neg)}">${esc(t.name)}</button>`;
    }).join('');
    document.getElementById('rpTopicSummary').textContent = filter.topic || `${topics.length}개 주제`;
    root.querySelectorAll('#rpVote button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.vote === filter.vote)));
    const list = rows.filter(r => matches(r));
    const active = filter.mood || filter.vote || filter.topic || filter.q;
    document.getElementById('rpCount').innerHTML = active ? `<b>${num(list.length)}건</b> / 전체 ${num(rows.length)}건` : `<b>총 ${num(rows.length)}건</b>`;
    document.getElementById('rpReset').hidden = !active;
    const moodLabel = Object.fromEntries(MOODS.map(m => [m.key, m]));
    document.getElementById('rpList').innerHTML = list.slice(0, shown).map(r => {
      const m = moodLabel[r._mood];
      const long = String(r.content || '').length > 180;
      return `<article class="rp-review ${m.cls}">
        <header>
          <span class="rp-mood ${m.cls}">${m.label}</span>
          <span class="rp-vote ${r._up ? 'up' : 'down'}">${r._up ? '추천' : '비추천'}</span>
          ${r.language ? `<span class="rp-lang">${esc(LANG_NAMES[r.language] || r.language)}</span>` : ''}
          <span class="rp-hours">${r.playtime_h === '' || r.playtime_h == null ? '플레이 시간 미상' : `${num(Math.round(Number(r.playtime_h)))}시간 플레이`}</span>
          <span class="rp-tags">${r._topics.map(t => `<em class="${t === filter.topic ? 'on' : ''}">${esc(t)}</em>`).join('')}</span>
        </header>
        ${r.key_phrase ? `<strong>${esc(r.key_phrase)}</strong>` : ''}
        <p class="${long ? 'is-clamped' : ''}">${esc(r.content)}</p>
        ${long ? '<button class="rp-text-btn" data-more>전체 보기</button>' : ''}
      </article>`;
    }).join('') + (list.length > shown ? `<button class="rp-more" data-page>리뷰 ${num(Math.min(PAGE, list.length - shown))}건 더 보기</button>` : '')
      + (list.length ? '' : '<div class="rp-card rp-empty">조건에 맞는 리뷰가 없습니다.</div>');
  }

  function onReviewsClick(e) {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.mood) filter.mood = filter.mood === b.dataset.mood ? '' : b.dataset.mood;
    else if (b.dataset.topic) filter.topic = filter.topic === b.dataset.topic ? '' : b.dataset.topic;
    else if (b.dataset.vote !== undefined) filter.vote = b.dataset.vote;
    else if (b.id === 'rpReset') { filter = {mood: '', vote: '', topic: '', q: ''}; document.getElementById('rpSearch').value = ''; }
    else if (b.hasAttribute('data-page')) { shown += PAGE; draw(); return; }
    else if (b.hasAttribute('data-more')) { const p = b.previousElementSibling; p.classList.toggle('is-clamped'); b.textContent = p.classList.contains('is-clamped') ? '전체 보기' : '접기'; return; }
    else return;
    shown = PAGE; draw();
  }

  /* ---------------- 수집 설계 ---------------- */
  function renderSample(data) {
    const box = document.getElementById('rpSample');
    if (!box) return;
    const sd = data?.sample_design_full || {};
    const pop = sd.population || {}, design = sd.design || {}, params = sd.params || {};
    const counts = data?.evidence?.counts || {};
    const collected = counts.collected ?? sd.actual?.total;
    const analyzed = counts.analyzed;
    const colNeg = counts.negative ?? sd.actual?.negative;
    if (!collected) { box.innerHTML = '<div class="rp-card rp-empty">수집 기록이 아직 없습니다.</div>'; return; }
    const colNegRate = colNeg != null ? colNeg / collected * 100 : null;
    const popNegRate = pop.total ? pop.negative / pop.total * 100 : null;
    const skipped = analyzed != null ? collected - analyzed : null;
    const ratio = popNegRate && colNegRate != null ? colNegRate / popNegRate : null;
    const balanceNote = ratio == null ? ''
      : ratio >= 1.3 ? `불만을 충분히 보려고 비추천 리뷰를 Steam 전체보다 <b>${ratio.toFixed(1)}배</b> 많은 비율로 모았습니다.`
      : ratio <= .77 ? `수집한 리뷰의 비추천 비율이 Steam 전체보다 낮습니다. 최신 리뷰 중 비추천이 적었기 때문일 수 있습니다.`
      : 'Steam 전체와 비슷한 비율로 모였습니다.';
    const bar = (label, sub, negRate) => negRate == null ? '' : `<div class="rp-bal-row">
        <span class="rp-bal-label"><b>${label}</b><small>${sub}</small></span>
        <span class="rp-bal-bar"><i class="up" style="width:${100 - negRate}%"><span>추천 ${pct(100 - negRate)}</span></i><i class="down" style="width:${negRate}%"></i></span>
        <span class="rp-bal-val">비추천 <b>${pct(negRate)}</b></span></div>`;
    const sortLabel = params.sort === 'helpful' ? '공감순' : '최신순';
    const since = params.since ? params.since.replaceAll('-', '.') : '';
    const lang = LANG_NAMES[params.language || data?.evidence?.language] || '';
    const langs = data?.evidence?.languages || [];
    box.innerHTML = designLogHTML(data?.design_log) + `
      <section class="rp-card">
        <h2>리뷰는 이렇게 좁혀졌습니다</h2>
        <div class="rp-flow">
          <div class="rp-step"><small>Steam ${esc(lang)} 리뷰 전체${since ? ' (전체 기간)' : ''}</small><b>${pop.total ? `${num(pop.total)}건` : '—'}</b>${pop.score ? `<span>${esc(pop.score)}</span>` : ''}</div>
          <div class="rp-arrow" aria-hidden="true">→</div>
          <div class="rp-step"><small>${sortLabel}으로 수집${since ? ` · ${since} 이후` : ''}</small><b>${num(collected)}건</b>${pop.total ? `<span>전체의 ${pct(collected / pop.total * 100)}</span>` : ''}</div>
          <div class="rp-arrow" aria-hidden="true">→</div>
          <div class="rp-step is-main"><small>AI가 분석</small><b>${num(analyzed)}건</b>${analyzed != null ? `<span>수집의 ${pct(analyzed / collected * 100)}</span>` : ''}</div>
        </div>
        ${analyzed != null ? `<div class="rp-split" role="img" aria-label="수집 ${collected}건 중 AI 분석 ${analyzed}건, 제외 ${skipped}건">
          <i class="done" style="flex:${analyzed} 1 0"><span>AI 분석 ${num(analyzed)}건</span></i><i class="skip" style="flex:${Math.max(skipped, 0)} 1 0"><span>${skipped / collected > .12 ? `짧아서 제외 ${num(skipped)}건` : ''}</span></i></div>
          <p class="rp-note">너무 짧아 주제를 알 수 없는 리뷰는 AI 분석에서 뺐습니다.</p>` : ''}
        ${langs.length > 1 ? `<p class="rp-note">수집한 리뷰의 언어: ${langs.map(([k, n]) => `${esc(LANG_NAMES[k] || k)} ${num(n)}건`).join(' · ')}</p>` : ''}
      </section>
      <section class="rp-card">
        <h2>추천·비추천 비율 비교</h2>
        <div class="rp-bal">
          ${bar('Steam 전체', pop.total ? `${num(pop.total)}건` : '', popNegRate)}
          ${bar('수집한 리뷰', `${num(collected)}건`, colNegRate)}
        </div>
        ${balanceNote ? `<p class="rp-callout">${balanceNote}</p>` : ''}
      </section>
      <section class="rp-card rp-caveat">
        <h2>이 숫자를 읽을 때</h2>
        <ul>
          <li><b>${sortLabel}으로 모은 리뷰입니다${since ? ` (${since} 이후)` : ''}.</b> 전체 유저를 무작위로 뽑은 표본이 아니므로 "전체 유저의 몇 %"로 읽으면 안 됩니다.</li>
          ${design.n_total ? `<li><b>처음 계획은 ${num(design.n_total)}건</b>(추천 ${num(design.n_pos)} / 비추천 ${num(design.n_neg)})이었습니다.${design.reason ? ` ${esc(design.reason)}.` : ''}</li>` : ''}
          ${params.min_neg ? `<li>불만을 볼 수 있도록 비추천을 최소 <b>${num(params.min_neg)}건</b> 모으도록 설정했습니다.</li>` : ''}
          ${sd.actual?.error_pct ? `<li class="rp-muted">참고: 무작위 표본이었다면 오차는 약 ±${sd.actual.error_pct}%p 수준입니다.</li>` : ''}
        </ul>
      </section>
      ${qualityHTML(data?.quality_report)}${usageHTML(data?.usage)}`;
  }

  // 분석 설계서: 단계마다 누가 정했는지(사람 · AI · 규칙)와 무엇을 정했는지
  function designLogHTML(rows) {
    if (!rows?.length) return '';
    const whoClass = w => w.startsWith('사람') ? 'human' : w.startsWith('AI') ? 'ai' : 'rule';
    return `<section class="rp-card rp-design">
        <h2>분석 설계서</h2>
        <p class="rp-design-lead">리뷰를 어떻게 가공할지는 기획자가 <b>규칙</b>으로 설계했습니다. 실행할 때 <b>사람</b>은 무엇을·얼마나만 고르고, <b>AI</b>는 주제를 제안하고 분류하며, 나머지는 규칙이 자동으로 처리합니다.</p>
        <ol class="rp-steps">${rows.map(r => `<li class="${whoClass(r.who)}">
          <span class="rp-step-name">${esc(r.step)}</span>
          <span class="rp-who ${whoClass(r.who)}">${esc(r.who)}</span>
          <span class="rp-step-text">${esc(r.text)}${r.details?.length ? `<ul>${r.details.map(d => `<li>${esc(d)}</li>`).join('')}</ul>` : ''}</span></li>`).join('')}</ol>
        <p class="rp-note">지킬 것·고칠 것은 조사를 시작할 곳입니다. 원문을 확인하고 기획에 반영하는 판단은 사람의 몫입니다.</p>
      </section>`;
  }

  // AI 사용량: 단계별 호출 수와 토큰. 비용은 설정한 단가로 계산한 추정치다.
  function usageHTML(u) {
    if (!u) return '';
    const stages = [['A', '주제 찾기'], ['B', '전체 분류'], ['C', '불만 심층'], ['D', '요약']].filter(([k]) => u[k]?.calls);
    if (!stages.length) return '';
    const tokens = k => (u[k].input || 0) + (u[k].output || 0);
    const total = stages.reduce((n, [k]) => n + tokens(k), 0) || 1;
    const price = u.pricing || {};
    const cost = stages.reduce((n, [k]) => n + (u[k].input || 0) * (price.input_per_1m || 0) + (u[k].output || 0) * (price.output_per_1m || 0), 0) / 1e6;
    return `<section class="rp-card">
        <h2>AI 사용량</h2>
        <div class="rp-split">${stages.map(([k, label], i) => `<i class="use-${i}" style="flex:${tokens(k)} 1 0" title="${label} ${num(tokens(k))} 토큰"><span>${tokens(k) / total > .12 ? label : ''}</span></i>`).join('')}</div>
        <div class="rp-use-list">${stages.map(([k, label], i) => `<span><i class="use-${i}"></i>${label} <b>${num(u[k].calls)}회</b> · ${num(tokens(k))} 토큰</span>`).join('')}</div>
        <p class="rp-note">모델 ${esc(u.model || '')} · 합계 ${num(total)} 토큰${cost ? ` · 설정 단가 기준 약 $${cost.toFixed(cost < 1 ? 3 : 2)}` : ''}. 본문이 같은 리뷰는 한 번만 보내고, 긴 리뷰는 앞·끝만 보내 토큰을 줄입니다.</p>
      </section>`;
  }

  // 품질 점검: 네 가지 점수를 같은 0~100 눈금 막대로. 80점 이상 통과, 60점 이상 주의.
  function qualityHTML(q) {
    if (!q || !q.dimensions) return '';
    const dims = [
      ['completeness', '완전성', '빠진 데이터가 없는가'],
      ['consistency', '일관성', 'AI 판단이 Steam 추천 여부와 크게 어긋나지 않는가'],
      ['representativeness', '대표성', '모은 리뷰의 추천 비율이 Steam 전체와 가까운가'],
      ['accuracy', '분석 가능성', '너무 짧거나 판단이 어려운 리뷰가 적은가']];
    const pass = q.thresholds?.pass ?? 80, warn = q.thresholds?.warn ?? 60;
    const tone = v => v >= pass ? 'ok' : v >= warn ? 'warn' : 'bad';
    const issues = dims.flatMap(([k]) => q.dimensions[k]?.issues || []).slice(0, 4);
    return `<section class="rp-card">
        <h2>분석 품질 점검 <span class="rp-grade ${tone(q.overall_score)}">${esc(q.grade_kr || '')} ${num(q.overall_score)}점</span></h2>
        <div class="rp-quality">${dims.map(([k, label, desc]) => {
          const v = q.dimensions[k]?.score;
          return v == null ? '' : `<div class="rp-q-row"><span class="rp-q-label"><b>${label}</b><small>${desc}</small></span><span class="rp-q-track"><i class="${tone(v)}" style="width:${Math.max(0, Math.min(100, v))}%"></i><em style="left:${pass}%"></em></span><span class="rp-q-val">${num(v)}</span></div>`;
        }).join('')}</div>
        <p class="rp-note">세로선 = 통과 기준 ${pass}점. 일관성은 정답 비교가 아닙니다. 게임을 추천하면서도 불만을 쓰는 리뷰가 있기 때문입니다.</p>
        ${issues.length ? `<ul class="rp-issues">${issues.map(i => `<li>${esc(i)}</li>`).join('')}</ul>` : ''}
      </section>`;
  }

  /* ---------------- 심층 분석 ---------------- */
  let deepTheme;
  function renderDeep(data) {
    const box = document.getElementById('rpDeep');
    if (!box) return;
    const deep = data?.evidence?.deep;
    if (!deep) { box.innerHTML = '<div class="rp-card rp-empty">분석 결과가 아직 없습니다.</div>'; return; }
    deepTheme = deep.causes.find(c => c.terms.length)?.theme || deep.causes[0]?.theme;
    box.innerHTML = `<div class="rp-deep">
      <section class="rp-card rp-deep-card" id="rpCauses"></section>
      <section class="rp-card rp-deep-card" id="rpChurn"></section>
      <section class="rp-card rp-deep-card" id="rpAgreed"></section>
      <section class="rp-card rp-deep-card" id="rpWants"></section></div>`;
    box.onclick = e => { const b = e.target.closest('[data-cause]'); if (b) { deepTheme = b.dataset.cause; drawCauses(deep); } };
    drawCauses(deep); drawChurn(deep); drawAgreed(deep); drawWants(deep);
  }
  // 카드 머리의 한 줄 인사이트. 한 장 보고서도 같은 문장을 쓴다.
  const churnGap = t => (t.early_share ?? 0) - (t.later_share ?? 0);
  const agreeGap = t => (t.vote_share || 0) - (t.count_share || 0);
  const churnPick = deep => [...deep.churn.topics].filter(t => t.early >= 2).sort((a, b) => churnGap(b) - churnGap(a))[0];
  const agreePick = deep => [...deep.agreed.topics].sort((a, b) => agreeGap(b) - agreeGap(a))[0];
  const lines = {
    cause: (deep, theme) => {
      const c = deep.causes.find(x => x.theme === theme), top = c?.terms[0];
      return top ? `<b>${esc(c.theme)}</b> 불만에서 가장 많이 나온 말은 <b>'${esc(top.word)}'</b>입니다 (${num(top.count)}건).` : '';
    },
    churn: deep => {
      const p = churnPick(deep), h = deep.early_hours;
      if (!deep.churn.early_n) return '';
      return p && churnGap(p) > 5 ? `${h}시간 전에 떠난 사람은 <b>'${esc(p.name)}'</b>을(를) 더 많이 말합니다 (${pct(p.early_share)} vs ${pct(p.later_share ?? 0)}).`
        : `${h}시간 전후로 비추천 이유가 크게 다르지 않습니다.`;
    },
    agreed: deep => {
      const p = agreePick(deep);
      if (!deep.agreed.total_votes) return '';
      return p && agreeGap(p) > 5 ? `<b>'${esc(p.name)}'</b> 불만은 건수로는 ${pct(p.count_share)}지만, 다른 유저의 공감은 ${pct(p.vote_share)}를 받았습니다.`
        : '공감은 불만 건수와 비슷하게 나뉘어 있습니다.';
    },
    wants: deep => deep.wants[0] ? `가장 많이 나온 요청은 <b>“${esc(deep.wants[0].text)}”</b>입니다 (${num(deep.wants[0].count)}건).` : '',
  };
  const noComplaints = '<p class="rp-empty">불만 리뷰의 AI 메모(complaints_v3.jsonl)가 없습니다. 분석을 다시 실행하면 채워집니다.</p>';
  const head = (n, title, insight) => `<span class="rp-deep-no">${n}</span><h2>${title}</h2>${insight ? `<p class="rp-insight">${insight}</p>` : ''}`;
  const hbar = (label, sub, value, max, text, cls = '') => `<div class="rp-hrow ${cls}"><span class="rp-hlabel"><b>${label}</b>${sub ? `<small>${sub}</small>` : ''}</span><span class="rp-htrack"><i style="width:${max ? value / max * 100 : 0}%"></i></span><span class="rp-hval">${text}</span></div>`;

  // ① 불만 세부 원인
  function drawCauses(deep) {
    const el = document.getElementById('rpCauses');
    const c = deep.causes.find(x => x.theme === deepTheme);
    const tabs = `<div class="rp-chips">${deep.causes.map(x => `<button class="rp-chip" data-cause="${esc(x.theme)}" aria-pressed="${x.theme === deepTheme}">${esc(x.theme)}</button>`).join('')}</div>`;
    if (!deep.has_complaints || !c) { el.innerHTML = head('①', '불만 세부 원인') + noComplaints; return; }
    const top = c.terms[0], max = top?.count || 1;
    el.innerHTML = head('①', '불만 세부 원인', lines.cause(deep, deepTheme))
      + tabs
      + (c.terms.length ? `<div class="rp-hbars">${c.terms.map((t, i) => hbar(esc(t.word), `“${esc(t.example)}”`, t.count, max, `${num(t.count)}건`, i ? '' : 'is-top')).join('')}</div>`
        : '<p class="rp-empty">여러 리뷰가 함께 쓴 말이 없습니다.</p>')
      + `<p class="rp-note">${esc(c.theme)} 불만 리뷰 ${num(c.reviews)}건에 AI가 적어 둔 문제·원인 메모에서, 두 리뷰 이상이 쓴 낱말입니다.</p>`;
  }

  // ② 초반 이탈 원인
  function drawChurn(deep) {
    const el = document.getElementById('rpChurn');
    const {early_n, later_n, topics} = deep.churn, h = deep.early_hours;
    if (!early_n) { el.innerHTML = head('②', '초반 이탈 원인') + `<p class="rp-empty">${h}시간 전에 비추천한 리뷰가 없습니다.</p>`; return; }
    const gap = churnGap, pick = churnPick(deep);
    const max = Math.max(...topics.flatMap(t => [t.early_share || 0, t.later_share || 0]), 1);
    el.innerHTML = head('②', '초반 이탈 원인', lines.churn(deep))
      + `<div class="rp-legend"><span class="early">${h}시간 전 비추천 ${num(early_n)}건</span><span class="later">${h}시간 뒤 비추천 ${num(later_n)}건</span></div>`
      + `<div class="rp-pairs">${topics.map(t => `<div class="rp-pair ${t === pick && gap(pick) > 5 ? 'is-top' : ''}"><b>${esc(t.name)}</b>
          <span class="rp-ptrack early"><i style="width:${(t.early_share || 0) / max * 100}%"></i><em>${pct(t.early_share ?? 0)}</em></span>
          <span class="rp-ptrack later"><i style="width:${(t.later_share || 0) / max * 100}%"></i><em>${pct(t.later_share ?? 0)}</em></span></div>`).join('')}</div>`
      + `<p class="rp-note">비율 = 각 묶음의 비추천 리뷰 중 그 주제를 불만으로 말한 비율. ${early_n < 30 ? `<b>${h}시간 전 비추천이 ${num(early_n)}건뿐이라 참고용입니다.</b>` : ''}</p>`;
  }

  // ③ 공감 많은 불만
  function drawAgreed(deep) {
    const el = document.getElementById('rpAgreed');
    const {topics, total_votes, reviews} = deep.agreed;
    if (!total_votes) { el.innerHTML = head('③', '공감 많은 불만') + '<p class="rp-empty">불만 리뷰에 "도움됨"이 눌린 기록이 없습니다.</p>'; return; }
    const gap = agreeGap, pick = agreePick(deep);
    const max = Math.max(...topics.flatMap(t => [t.vote_share || 0, t.count_share || 0]), 1);
    const quote = reviews[0];
    el.innerHTML = head('③', '공감 많은 불만', lines.agreed(deep))
      + `<div class="rp-legend"><span class="later">불만 건수 비율</span><span class="agree">공감(도움됨) 비율</span></div>`
      + `<div class="rp-pairs">${topics.map(t => `<div class="rp-pair ${t === pick && gap(pick) > 5 ? 'is-top' : ''}"><b>${esc(t.name)}</b>
          <span class="rp-ptrack later"><i style="width:${(t.count_share || 0) / max * 100}%"></i><em>${pct(t.count_share)}</em></span>
          <span class="rp-ptrack agree"><i style="width:${(t.vote_share || 0) / max * 100}%"></i><em>${pct(t.vote_share)} · ${num(t.votes)}</em></span></div>`).join('')}</div>`
      + (quote ? `<figure class="rp-quote"><figcaption>가장 공감받은 불만 · 도움됨 ${num(quote.helpful)} · ${quote.themes.map(esc).join(', ')}</figcaption><blockquote>“${esc(quote.content)}${quote.truncated ? '…' : ''}”</blockquote></figure>` : '');
  }

  // ④ 유저가 원하는 것
  function drawWants(deep) {
    const el = document.getElementById('rpWants');
    if (!deep.has_complaints) { el.innerHTML = head('④', '유저가 원하는 것') + noComplaints; return; }
    const list = deep.wants;
    el.innerHTML = head('④', '유저가 원하는 것', lines.wants(deep))
      + (list.length ? `<ol class="rp-wants">${list.map(w => `<li><span class="rp-want-text">${esc(w.text)}</span><span class="rp-want-meta"><em>${esc(w.theme)}</em>${num(w.count)}건 · 공감 ${num(w.votes)}</span></li>`).join('')}</ol>`
        : '<p class="rp-empty">구체적인 요청 문장이 없습니다.</p>')
      + '<p class="rp-note">불만 리뷰에서 "~해 주세요", "~했으면" 같은 구체적인 요청만 모았습니다. "버그 수정"처럼 막연한 말은 뺐습니다.</p>';
  }

  // 한 장 보고서용: 심층 분석 네 줄 (비어 있는 줄은 뺌)
  function deepLines(deep) {
    if (!deep) return [];
    const theme = deep.causes.find(c => c.terms.length)?.theme;
    return [['불만 세부 원인', deep.has_complaints ? lines.cause(deep, theme) : ''], ['초반 이탈', lines.churn(deep)],
            ['공감', lines.agreed(deep)], ['유저 요청', deep.has_complaints ? lines.wants(deep) : '']].filter(([, t]) => t);
  }

  return {renderReviews, renderSample, renderDeep, deepLines};
})();
