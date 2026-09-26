/* 리뷰 진단 화면. 한 문장 결론 → 주제별 칭찬·불만 차트 → 선택 주제 근거 → 플레이 시간.
   모든 막대와 문장은 현재 게임의 evidence 집계로만 그린다. 설계 규칙은 AGENTS.md 참고. */
window.ReviewDashboard = (() => {
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = x => x == null ? '—' : Number(x).toLocaleString('ko-KR');
  const pct = x => x == null ? '—' : `${Number(x).toFixed(1)}%`;
  const clamp = x => Math.max(0, Math.min(100, Number(x) || 0));
  const COLLAPSED_ROWS = 10, MAX_CONCERN_ROWS = 4;
  let data, evidence, appId, root, selected, expanded = false;
  let dialogTheme, dialogSentiment, dialogPage, request, restoreFocus;

  // 받침 유무로 은/는을 고른다. 한글이 아니면 둘 다 적는다.
  function topicJosa(word) {
    const code = String(word).trim().slice(-1).charCodeAt(0) - 0xAC00;
    if (code < 0 || code > 11171) return '은(는)';
    return code % 28 ? '은' : '는';
  }

  // 칭찬이 더 많은 주제는 칭찬순, 불만이 더 많은 주제는 불만순. 두 묶음의 첫 줄이 곧 결론이다.
  function groups() {
    const praised = evidence.themes.filter(t => t.pos >= t.neg && t.mentions > 0)
      .sort((a,b) => b.pos - a.pos || a.neg - b.neg || a.name.localeCompare(b.name));
    const disliked = evidence.themes.filter(t => t.neg > t.pos)
      .sort((a,b) => b.neg - a.neg || a.pos - b.pos || a.name.localeCompare(b.name));
    return {praised, disliked};
  }
  function strength() { return groups().praised.find(t => t.pos > 0); }
  function concern() { return groups().disliked[0]; }
  // 불만이 앞서는 주제가 없을 때 보조로 보여줄 가장 많은 불만
  function loudest() { return [...evidence.themes].filter(t => t.neg > 0).sort((a,b) => b.neg - a.neg)[0]; }
  function themeByName(name) { return evidence.themes.find(t => t.name === name); }
  function role(t) {
    if (!t) return null;
    if (t.name === concern()?.name) return 'concern';
    if (t.name === strength()?.name) return 'strength';
    if (!concern() && t.name === loudest()?.name) return 'watch';
    return t.neg > t.pos ? 'disliked' : 'praised';
  }

  function updateURL() {
    const url = new URL(location.href);
    url.searchParams.set('topic', selected);
    url.searchParams.delete('topic_sort');
    history.replaceState(null, '', url);
  }

  function verdictHTML() {
    const s = strength(), c = concern(), loud = loudest();
    const pos = t => `<span class="rd-hl rd-hl-pos">${esc(t.name)}</span>${topicJosa(t.name)}`;
    const neg = t => `<span class="rd-hl rd-hl-neg">${esc(t.name)}</span>${topicJosa(t.name)}`;
    if (s && c) return `${pos(s)} 지키고, ${neg(c)} 고쳐야 합니다`;
    if (c) return `${neg(c)} 고쳐야 합니다`;
    if (s && loud) return `${pos(s)} 지키고, <span class="rd-hl rd-hl-neg">${esc(loud.name)}</span> 불만을 살펴보세요`;
    if (s) return `${pos(s)} 가장 큰 강점입니다`;
    return '아직 분류된 주제가 없습니다';
  }

  function render(V, id) {
    request?.abort();
    data = V; evidence = V.evidence; appId = id;
    root = document.getElementById('ovBody');
    root.className = 'rd';
    const art = document.getElementById('rdPageArt');
    art.innerHTML = V.game?.header_image
      ? `<img src="${esc(V.game.header_image)}" alt="" onerror="this.remove()" />` : '';
    document.getElementById('rdPageActions').innerHTML = `<button class="rd-btn" type="button" onclick="startNewAnalysis(${Number(id)},null,null,true)">추가 수집</button><a class="rd-btn" href="/api/reviews/download?app_id=${Number(id)}" download>원문 내려받기</a><a class="rd-btn primary" href="/api/analysis/download?app_id=${Number(id)}" download>분석 결과 내려받기</a>`;
    if (!evidence) {
      document.getElementById('overviewTitle').textContent = `${V.game?.name || '게임'} 리뷰 진단`;
      document.getElementById('ovCoverage').textContent = '';
      root.innerHTML = '<div class="rd-card rd-empty">이 분석에는 원문 연결 데이터가 없습니다. 추가 분석 후 주제별 근거를 확인할 수 있습니다.</div>';
      return;
    }
    const counts = evidence.counts;
    const language = ({koreana:'한국어',english:'영어',all:'전체 언어',japanese:'일본어',schinese:'중국어 간체',unknown:'언어 정보 없음'})[evidence.language] || evidence.language;
    const period = evidence.period ? `${evidence.period.start.replaceAll('-','.')} – ${evidence.period.end.replaceAll('-','.')}` : '기간 정보 없음';
    document.getElementById('overviewTitle').innerHTML = verdictHTML();
    document.getElementById('ovCoverage').innerHTML = `<span class="rd-game-name">${esc(V.game?.name || '게임')} 리뷰 진단</span><span>${esc(language)} Steam 리뷰</span><span>${esc(period)}</span><span>AI 분석 <b>${num(counts.analyzed)}건</b> / 수집 ${num(counts.collected)}건</span>`;

    const params = new URLSearchParams(location.search);
    selected = themeByName(params.get('topic'))?.name || concern()?.name || strength()?.name || evidence.themes[0]?.name;
    expanded = false;
    root.innerHTML = `
      <div class="rd-hero">
        <section class="rd-chart-card" aria-labelledby="rdTopicsTitle">
          <div class="rd-chart-head">
            <h2 id="rdTopicsTitle">주제별 칭찬과 불만</h2>
            <p>리뷰 수 · 주제를 누르면 근거가 나옵니다</p>
          </div>
          <div id="rdTopicChart"></div>
          <div class="rd-chart-foot">
            <span>AI 분석 리뷰 ${num(counts.analyzed)}건 기준 · 한 리뷰가 여러 주제에 들어갈 수 있음</span>
            <button class="rd-text-btn" data-action="method">분석 기준</button>
          </div>
        </section>
        <aside class="rd-focus" id="rdDetail" aria-live="polite" aria-label="선택한 주제의 근거"></aside>
      </div>
      <section class="rd-when" aria-labelledby="rdWhenTitle">
        <div class="rd-when-head"><h2 id="rdWhenTitle">플레이 시간별 비추천율</h2><p>수집 리뷰 ${num(counts.collected)}건 · 작성 당시 플레이 시간 기준 · 점선은 전체 ${pct(evidence.sample_negative_rate)}</p></div>
        <div id="rdCohortChart"></div>
      </section>
      <dialog class="rd-dialog rd-method-dialog" id="rdMethodDialog" aria-labelledby="rdMethodTitle"><div class="rd-dialog-head"><div><h2 id="rdMethodTitle">분석 기준</h2><p>${num(counts.collected)}건 수집 · ${num(counts.analyzed)}건 AI 분석</p></div><button class="rd-btn" data-action="close-method" aria-label="분석 기준 닫기">닫기 ×</button></div><div class="rd-method-grid">
        <p><b>차트 읽는 법</b><br>막대 길이는 해당 주제를 칭찬하거나 불만으로 언급한 AI 분석 리뷰 수입니다. 양쪽이 같은 눈금을 씁니다. 칭찬이 더 많은 주제는 위에서 칭찬순, 불만이 더 많은 주제는 아래 구역에서 불만순으로 놓입니다.</p>
        <p><b>지킬 것 · 고칠 것</b><br>지킬 것은 칭찬이 더 많은 주제 중 칭찬 리뷰가 가장 많은 주제, 고칠 것은 불만이 더 많은 주제 중 불만 리뷰가 가장 많은 주제입니다. 조사를 시작할 곳이지 개선 효과나 우선순위를 증명하지 않습니다.</p>
        <p><b>수집 범위</b><br>최신순으로 수집한 리뷰입니다. 추천·비추천 비율을 맞춰도 전체 유저나 전체 기간의 무작위 표본이 되지는 않습니다. 리뷰는 자발적으로 작성한 의견입니다.</p>
        <p><b>표본과 AI 분류</b><br>주제 수치는 AI가 원문을 분류한 결과입니다. 짧은 리뷰 등 ${num(counts.collected - counts.analyzed)}건은 주제 분석에 포함되지 않습니다. 플레이 시간별 비추천율은 수집 리뷰 전체의 Steam 추천 여부로 계산합니다.${counts.skipped_analysis ? ` 읽을 수 없거나 원문이 없는 분석 ${num(counts.skipped_analysis)}건 제외.` : ''}</p>
      </div></dialog>
      <dialog class="rd-dialog" id="rdEvidenceDialog" aria-labelledby="rdDialogTitle"><div class="rd-dialog-head"><div><h2 id="rdDialogTitle">리뷰 근거</h2><p id="rdDialogMeta"></p></div><button class="rd-btn" data-action="close-dialog" aria-label="리뷰 근거 닫기">닫기 ×</button></div><div class="rd-toggle" aria-label="주제 감성 선택"><button data-action="evidence-filter" data-sentiment="N">불만</button><button data-action="evidence-filter" data-sentiment="P">칭찬</button><button data-action="evidence-filter" data-sentiment="all">전체</button></div><div id="rdEvidenceBody" aria-live="polite"></div></dialog>`;
    root.onclick = onClick;
    const dialog = document.getElementById('rdEvidenceDialog');
    dialog.addEventListener('click', event => { if (event.target === dialog) closeDialog(); });
    dialog.addEventListener('close', () => { request?.abort(); restoreFocus?.focus(); });
    const methodDialog = document.getElementById('rdMethodDialog');
    methodDialog.addEventListener('click', event => { if (event.target === methodDialog) closeMethod(); });
    methodDialog.addEventListener('close', () => restoreFocus?.focus());
    renderTopics(); renderDetail(); renderCohorts();
  }

  // 나비형 막대: 가운데 0선에서 왼쪽 불만, 오른쪽 칭찬. 두 방향이 같은 눈금이라 0선 위치는 최대값 비율로 정한다.
  function renderTopics() {
    const target = document.getElementById('rdTopicChart');
    const {praised, disliked} = groups();
    if (!praised.length && !disliked.length) { target.innerHTML = '<div class="rd-empty">분류된 주제가 아직 없습니다.</div>'; return; }
    const maxNeg = Math.max(1, ...evidence.themes.map(t => t.neg));
    const maxPos = Math.max(1, ...evidence.themes.map(t => t.pos));
    const gutter = 9, span = 100 - gutter * 2;
    const zero = gutter + span * maxNeg / (maxNeg + maxPos);
    const w = v => span * v / (maxNeg + maxPos);
    let top = praised, bottom = disliked, hidden = 0;
    if (!expanded && praised.length + disliked.length > COLLAPSED_ROWS) {
      bottom = disliked.slice(0, MAX_CONCERN_ROWS);
      top = praised.slice(0, COLLAPSED_ROWS - bottom.length);
      const chosen = themeByName(selected);
      if (chosen && ![...top, ...bottom].includes(chosen)) (chosen.neg > chosen.pos ? bottom : top).splice(-1, 1, chosen);
      hidden = praised.length + disliked.length - top.length - bottom.length;
    }
    const tags = {strength:'지킬 것', concern:'고칠 것', watch:'살펴볼 것'};
    const row = t => {
      const r = role(t), negW = w(t.neg), posW = w(t.pos);
      return `<button class="rd-row is-${r}" data-action="select" data-theme="${esc(t.name)}" aria-pressed="${selected === t.name}" aria-label="${esc(t.name)}: 칭찬 ${t.pos}건, 불만 ${t.neg}건${tags[r] ? `, ${tags[r]}` : ''}" title="${esc(t.name)} · 칭찬 ${num(t.pos)} · 불만 ${num(t.neg)}">
        <span class="rd-row-name">${esc(t.name)}</span>
        <span class="rd-row-plot">
          ${t.neg ? `<i class="rd-bar rd-bar-neg" style="right:${100 - zero}%;width:${negW}%"></i>` : ''}
          <b class="rd-val rd-val-neg" style="right:calc(${100 - zero + negW}% + 6px)">${num(t.neg)}</b>
          ${t.pos ? `<i class="rd-bar rd-bar-pos" style="left:${zero}%;width:${posW}%"></i>` : ''}
          <b class="rd-val rd-val-pos" style="left:calc(${zero + posW}% + 6px)">${num(t.pos)}</b>
        </span>
        <span class="rd-row-tag">${tags[r] ? `<em>${tags[r]}</em>` : ''}</span>
      </button>`;
    };
    target.innerHTML = `
      <div class="rd-axis-head" aria-hidden="true"><span></span><span class="rd-axis-labels" style="--zero:${zero}%"><b class="neg">← 불만</b><b class="pos">칭찬 →</b></span><span></span></div>
      <div class="rd-rows" style="--zero:${zero}%">
        ${top.map(row).join('')}
        ${hidden ? `<button class="rd-row-more" data-action="expand">⋯ 주제 ${hidden}개 더 보기</button>` : ''}
        ${bottom.length ? `<div class="rd-zone" role="presentation"><span>불만이 칭찬보다 많은 주제</span></div>${bottom.map(row).join('')}` : ''}
        ${expanded && praised.length + disliked.length > COLLAPSED_ROWS ? '<button class="rd-row-more" data-action="expand">접기 ↑</button>' : ''}
      </div>`;
  }

  // 선택 주제: 칭찬/불만 비율, 불만이 나오는 플레이 구간, AI 요약, 실제 리뷰 한 줄
  function renderDetail() {
    const t = themeByName(selected), target = document.getElementById('rdDetail');
    if (!t) { target.innerHTML = '<div class="rd-empty">확인할 주제가 없습니다.</div>'; return; }
    const r = role(t), total = t.pos + t.neg;
    const negShare = total ? t.neg / total * 100 : 0;
    const label = {strength:'지킬 것', concern:'고칠 것', watch:'살펴볼 것', disliked:'불만 우세', praised:'칭찬 우세'}[r];
    const definition = data.themes?.find(row => row.name === t.name)?.desc;
    const action = data.actions?.find(row => row.theme === t.name);
    const lead = t.neg > t.pos ? 'N' : 'P';
    const quote = t.examples?.[lead]?.[0] || t.examples?.[lead === 'N' ? 'P' : 'N']?.[0];
    const cells = (t.cells || []).map((c, i) => ({...c, label: evidence.cohorts[i]?.label || ''}));
    const reliable = cells.filter(c => c.denominator >= 30 && c.rate != null);
    const cellMax = Math.max(1, ...reliable.map(c => c.rate));
    const when = t.neg && cells.length ? `<div class="rd-focus-block">
        <h3>이 불만이 나오는 플레이 구간</h3>
        <div class="rd-cols" role="img" aria-label="${cells.map(c => `${c.label} ${c.denominator ? pct(c.rate) : '자료 없음'}`).join(', ')}">
          ${cells.map(c => { const small = c.denominator < 30; const h = small || c.rate == null ? 0 : Math.max(4, c.rate / cellMax * 100);
            return `<div class="rd-col ${small ? 'is-small' : ''}" title="${esc(c.label)} · ${num(c.count)} / ${num(c.denominator)}건${small ? ' · 표본 적음' : ''}"><span class="rd-col-val">${small ? '표본 적음' : pct(c.rate)}</span><span class="rd-col-track"><i style="height:${h}%"></i></span><span class="rd-col-label">${esc(c.label)}</span></div>`; }).join('')}
        </div>
        <p class="rd-note">구간별 AI 분석 리뷰 중 이 주제 불만 비율 · 30건 미만 구간은 표시하지 않음</p>
      </div>` : '';
    target.className = `rd-focus is-${r}`;
    target.innerHTML = `
      <div class="rd-focus-head">
        <span class="rd-focus-kicker">선택한 주제 <em>${label}</em></span>
        <h2>${esc(t.name)}</h2>
        ${definition ? `<p>${esc(definition)}</p>` : ''}
      </div>
      <div class="rd-split" role="img" aria-label="불만 ${t.neg}건, 칭찬 ${t.pos}건">
        <div class="rd-split-labels"><span class="neg"><b>${num(t.neg)}</b> 불만 ${Math.round(negShare)}%</span><span class="pos">칭찬 ${Math.round(100 - negShare)}% <b>${num(t.pos)}</b></span></div>
        <div class="rd-split-bar"><i class="neg" style="width:${negShare}%"></i><i class="pos" style="width:${100 - negShare}%"></i></div>
      </div>
      ${when}
      ${action?.prob ? `<div class="rd-focus-block rd-ai"><h3>AI 요약</h3><p>${esc(action.prob)}</p></div>` : ''}
      ${quote ? `<figure class="rd-quote"><figcaption>실제 리뷰 · ${quote.recommended ? '게임 추천' : '게임 비추천'}${quote.hours == null ? '' : ` · ${num(Math.round(quote.hours))}시간`}</figcaption><blockquote>“${esc(quote.content)}${quote.truncated ? '…' : ''}”</blockquote></figure>` : ''}
      <div class="rd-focus-actions">
        ${t.neg ? `<button class="rd-btn ${lead === 'N' ? 'primary' : ''}" data-action="evidence" data-sentiment="N">불만 리뷰 ${num(t.neg)}건</button>` : ''}
        ${t.pos ? `<button class="rd-btn ${lead === 'P' ? 'primary' : ''}" data-action="evidence" data-sentiment="P">칭찬 리뷰 ${num(t.pos)}건</button>` : ''}
      </div>`;
  }

  function renderCohorts() {
    const base = evidence.sample_negative_rate;
    const rows = evidence.cohorts.filter(c => c.n > 0);
    const target = document.getElementById('rdCohortChart');
    if (!rows.length) { target.innerHTML = '<div class="rd-empty">작성 당시 플레이 시간이 있는 리뷰가 없습니다.</div>'; return; }
    const max = Math.max(10, base || 0, ...rows.filter(c => !c.small).map(c => c.negative_rate || 0)) * 1.15;
    const x = v => clamp(v / max * 100);
    target.innerHTML = `<div class="rd-cohorts">${rows.map(c => `<div class="rd-cohort ${c.small ? 'is-small' : ''}">
        <span class="rd-cohort-label"><b>${esc(c.label)}</b><small>${num(c.n)}건</small></span>
        <span class="rd-cohort-track" role="img" aria-label="${esc(c.label)}, ${num(c.n)}건 중 비추천 ${num(c.negative)}건, ${pct(c.negative_rate)}${c.small ? ', 표본 적음' : ''}">
          ${base == null ? '' : `<i class="rd-cohort-base" style="left:${x(base)}%"></i>`}
          ${c.negative_rate == null || c.small ? '' : `<i class="rd-cohort-fill" style="width:${x(c.negative_rate)}%"></i>`}
        </span>
        <span class="rd-cohort-val">${c.small ? `<small>표본 적음 (${num(c.negative)}/${num(c.n)}건)</small>` : pct(c.negative_rate)}</span>
      </div>`).join('')}</div>`;
  }

  function onClick(event) {
    const button = event.target.closest('[data-action]');
    if (!button) return;
    const action = button.dataset.action;
    if (action === 'select') {
      if (!themeByName(button.dataset.theme)) return;
      selected = button.dataset.theme; updateURL(); renderTopics(); renderDetail();
      // 좁은 화면에서는 근거 패널이 차트 아래에 있으므로 그쪽으로 이동
      if (innerWidth < 1080) document.getElementById('rdDetail')?.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
    } else if (action === 'expand') { expanded = !expanded; renderTopics(); }
    else if (action === 'method') { restoreFocus=button; document.getElementById('rdMethodDialog').showModal(); }
    else if (action === 'evidence') {
      restoreFocus = button; dialogTheme=selected; dialogSentiment=button.dataset.sentiment; dialogPage=1;
      document.getElementById('rdEvidenceDialog').showModal(); loadEvidence();
    } else if (action === 'close-dialog') closeDialog();
    else if (action === 'close-method') closeMethod();
    else if (action === 'evidence-filter') { dialogSentiment=button.dataset.sentiment; dialogPage=1; loadEvidence(); }
    else if (action === 'evidence-page') { dialogPage=Number(button.dataset.page); loadEvidence(); }
    else if (action === 'retry-evidence') loadEvidence();
  }
  function closeDialog() { document.getElementById('rdEvidenceDialog').close(); }
  function closeMethod() { document.getElementById('rdMethodDialog').close(); }
  async function loadEvidence() {
    request?.abort(); request = new AbortController();
    const controller=request, body=document.getElementById('rdEvidenceBody');
    document.getElementById('rdDialogTitle').textContent = `${dialogTheme} · 리뷰 근거`;
    document.getElementById('rdDialogMeta').textContent = 'AI 주제 분류 · 원문을 직접 확인하세요 · 공감 수, 최신순';
    root.querySelectorAll('[data-action="evidence-filter"]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.sentiment===dialogSentiment)));
    body.innerHTML='<p class="rd-empty">원문을 불러오는 중…</p>';
    try {
      const params=new URLSearchParams({app_id:appId,theme:dialogTheme,sentiment:dialogSentiment,page:dialogPage});
      const response=await fetch(`/dashboard/evidence?${params}`,{signal:controller.signal});
      if (!response.ok) throw new Error('evidence unavailable');
      const result=await response.json();
      if(controller!==request) return;
      body.innerHTML = result.reviews.map(r=>`<article class="rd-review"><header><b>${r.recommended?'게임 추천':'게임 비추천'}</b><span>작성 당시 ${r.hours==null?'플레이 시간 미상':`${num(Math.round(r.hours*10)/10)}시간`}</span><span>공감 ${num(r.helpful)}</span></header><p>${esc(r.content)}${r.truncated?'…':''}</p>${r.url?`<a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">Steam에서 원문 보기 ↗</a>`:''}</article>`).join('') || '<p class="rd-empty">이 분류에 해당하는 리뷰가 없습니다.</p>';
      const pages=Math.max(1,Math.ceil(result.total/result.page_size));
      body.innerHTML+=`<div class="rd-pagination"><button class="rd-btn" data-action="evidence-page" data-page="${dialogPage-1}" ${dialogPage<=1?'disabled':''}>이전</button><span>${num(result.total)}건 · ${dialogPage} / ${pages}</span><button class="rd-btn" data-action="evidence-page" data-page="${dialogPage+1}" ${dialogPage>=pages?'disabled':''}>다음</button></div>`;
    } catch(error) {
      if(error.name==='AbortError') return;
      body.innerHTML='<p class="rd-empty">원문을 불러오지 못했습니다. <button class="rd-btn" data-action="retry-evidence">다시 시도</button></p>';
    }
  }
  return {render};
})();
