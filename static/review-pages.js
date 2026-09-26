/* 리뷰 원문 · 수집 설계 화면. 데이터는 /dashboard/data/v5 응답(DATA)만 쓴다. */
window.ReviewPages = (() => {
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
        </div>
        <div class="rp-filter-row">
          <span class="rp-label">주제</span>
          <div class="rp-chips" id="rpTopics"></div>
        </div>
        <div class="rp-filter-row">
          <span class="rp-label">Steam 평가</span>
          <div class="rp-toggle" id="rpVote"><button data-vote="">전체</button><button data-vote="up">추천</button><button data-vote="down">비추천</button></div>
          <input class="rp-search" id="rpSearch" type="search" placeholder="리뷰 내용 검색" aria-label="리뷰 내용 검색" />
        </div>
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
      return `<button class="rp-seg ${m.cls} ${filter.mood && filter.mood !== m.key ? 'is-dim' : ''}" data-mood="${m.key}" style="flex:${w} 1 0" aria-pressed="${filter.mood === m.key}" title="${m.label} ${num(n)}건 (${pct(w)})"><span>${w >= 9 ? `${m.label} ${Math.round(w)}%` : ''}</span></button>`;
    }).join('');
    // 주제 칩: 주제마다 불만 비율을 작은 막대로
    document.getElementById('rpTopics').innerHTML = topics.map(t => {
      const neg = t.mentions ? t.neg / t.mentions * 100 : 0;
      return `<button class="rp-chip ${t.neg > t.pos ? 'is-neg' : ''}" data-topic="${esc(t.name)}" aria-pressed="${filter.topic === t.name}" title="${esc(t.name)} · 칭찬 ${num(t.pos)} · 불만 ${num(t.neg)}">${esc(t.name)}<i class="rp-chip-bar"><b style="width:${neg}%"></b></i></button>`;
    }).join('');
    root.querySelectorAll('#rpVote button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.vote === filter.vote)));
    const list = rows.filter(r => matches(r));
    const active = filter.mood || filter.vote || filter.topic || filter.q;
    document.getElementById('rpCount').innerHTML = `<b>${num(list.length)}건</b> / 전체 ${num(rows.length)}건`;
    document.getElementById('rpReset').hidden = !active;
    const moodLabel = Object.fromEntries(MOODS.map(m => [m.key, m]));
    document.getElementById('rpList').innerHTML = list.slice(0, shown).map(r => {
      const m = moodLabel[r._mood];
      const long = String(r.content || '').length > 180;
      return `<article class="rp-review ${m.cls}">
        <header>
          <span class="rp-mood ${m.cls}">${m.label}</span>
          <span class="rp-vote ${r._up ? 'up' : 'down'}">${r._up ? '추천' : '비추천'}</span>
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
    const lang = ({koreana:'한국어', english:'영어', japanese:'일본어', schinese:'중국어 간체', all:'전체 언어'})[params.language || data?.evidence?.language] || '';
    box.innerHTML = `
      <section class="rp-card">
        <h2>리뷰는 이렇게 좁혀졌습니다</h2>
        <div class="rp-flow">
          <div class="rp-step"><small>Steam ${esc(lang)} 리뷰 전체</small><b>${pop.total ? `${num(pop.total)}건` : '—'}</b>${pop.score ? `<span>${esc(pop.score)}</span>` : ''}</div>
          <div class="rp-arrow" aria-hidden="true">→</div>
          <div class="rp-step"><small>최신순으로 수집</small><b>${num(collected)}건</b>${pop.total ? `<span>전체의 ${pct(collected / pop.total * 100)}</span>` : ''}</div>
          <div class="rp-arrow" aria-hidden="true">→</div>
          <div class="rp-step is-main"><small>AI가 분석</small><b>${num(analyzed)}건</b>${analyzed != null ? `<span>수집의 ${pct(analyzed / collected * 100)}</span>` : ''}</div>
        </div>
        ${analyzed != null ? `<div class="rp-split" role="img" aria-label="수집 ${collected}건 중 AI 분석 ${analyzed}건, 제외 ${skipped}건">
          <i class="done" style="flex:${analyzed} 1 0"><span>AI 분석 ${num(analyzed)}건</span></i><i class="skip" style="flex:${Math.max(skipped, 0)} 1 0"><span>${skipped / collected > .12 ? `짧아서 제외 ${num(skipped)}건` : ''}</span></i></div>
          <p class="rp-note">너무 짧아 주제를 알 수 없는 리뷰는 AI 분석에서 뺐습니다.</p>` : ''}
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
          <li><b>최신순으로 모은 리뷰입니다.</b> 전체 유저를 무작위로 뽑은 표본이 아니므로 "전체 유저의 몇 %"로 읽으면 안 됩니다.</li>
          ${design.n_total ? `<li><b>처음 계획은 ${num(design.n_total)}건</b>(추천 ${num(design.n_pos)} / 비추천 ${num(design.n_neg)})이었습니다.${design.reason ? ` ${esc(design.reason)}.` : ''}</li>` : ''}
          ${params.min_neg ? `<li>불만을 볼 수 있도록 비추천을 최소 <b>${num(params.min_neg)}건</b> 모으도록 설정했습니다.</li>` : ''}
          ${sd.actual?.error_pct ? `<li class="rp-muted">참고: 무작위 표본이었다면 오차는 약 ±${sd.actual.error_pct}%p 수준입니다.</li>` : ''}
        </ul>
      </section>`;
  }

  return {renderReviews, renderSample};
})();
