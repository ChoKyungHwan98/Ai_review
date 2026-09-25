/* Visual review diagnosis. All marks are computed from the current game's data. */
window.ReviewDashboard = (() => {
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = x => x == null ? '—' : Number(x).toLocaleString('ko-KR');
  const pct = x => x == null ? '—' : `${Number(x).toFixed(1)}%`;
  const signed = x => x == null ? '—' : `${x > 0 ? '+' : x < 0 ? '−' : ''}${Math.abs(x).toFixed(2)}%p`;
  const clamp = x => Math.max(0, Math.min(100, Number(x) || 0));
  const blue = '#3182F6', orange = '#F04452';
  let data, evidence, appId, root, selected, sort = 'negative', expanded = false;
  let dialogTheme, dialogSentiment, dialogPage, request, restoreFocus;

  function updateURL() {
    const url = new URL(location.href);
    url.searchParams.set('topic', selected);
    url.searchParams.set('topic_sort', sort);
    history.replaceState(null, '', url);
  }

  function themeByName(name) { return evidence.themes.find(t => t.name === name); }
  function topConcern() { return [...evidence.themes].filter(t => t.neg > 0).sort((a,b) => b.neg - a.neg || b.mentions - a.mentions)[0]; }
  function topAssociation() {
    return [...evidence.themes].filter(t => t.neg > 0 && t.mentions >= 5 && t.exclusion_delta > 0)
      .sort((a,b) => b.exclusion_delta - a.exclusion_delta || b.neg - a.neg)[0];
  }
  function topStrength() { return [...evidence.themes].filter(t => t.pos > 0).sort((a,b) => b.pos - a.pos)[0]; }
  function smallCohort() {
    const base = evidence.sample_negative_rate;
    return [...evidence.cohorts].filter(c => c.small && c.n >= 5 && c.negative_rate != null &&
      base != null && c.negative_rate >= base + 10)
      .sort((a,b) => b.negative_rate - a.negative_rate || b.n - a.n)[0];
  }

  function render(V, id) {
    request?.abort();
    data = V; evidence = V.evidence; appId = id;
    root = document.getElementById('ovBody');
    root.className = 'rd';
    if (!evidence) {
      root.innerHTML = '<div class="rd-card rd-empty">이 분석에는 원문 연결 데이터가 없습니다. 추가 분석 후 주제별 근거를 확인할 수 있습니다.</div>';
      return;
    }
    const params = new URLSearchParams(location.search);
    const concern = topConcern(), strength = topStrength(), counts = evidence.counts;
    selected = themeByName(params.get('topic'))?.name || concern?.name || strength?.name || evidence.themes[0]?.name;
    sort = params.get('topic_sort') === 'mentions' ? 'mentions' : 'negative';
    expanded = false;
    const small = smallCohort();
    const insightScale = Math.max(1, Number(strength?.pos)||0, Number(strength?.neg)||0, Number(concern?.pos)||0, Number(concern?.neg)||0);
    const insightBalance = theme => {
      const neg = clamp((Number(theme?.neg)||0) / insightScale * 100);
      const pos = clamp((Number(theme?.pos)||0) / insightScale * 100);
      return `<span class="rd-mini-balance" role="img" aria-label="불만 ${num(theme?.neg)}건, 칭찬 ${num(theme?.pos)}건"><span class="rd-mini-half rd-mini-neg"><i style="width:${neg}%"></i></span><span class="rd-mini-zero"></span><span class="rd-mini-half rd-mini-pos"><i style="width:${pos}%"></i></span></span><span class="rd-mini-values"><span>불만 ${num(theme?.neg)}</span><span>칭찬 ${num(theme?.pos)}</span></span>`;
    };
    const complaintRate = counts.complaint_reviews ? counts.recommended_complaints / counts.complaint_reviews * 100 : null;
    const complaintNotRecommended = Math.max(0, counts.complaint_reviews - counts.recommended_complaints);
    const language = ({koreana:'한국어',english:'영어',all:'전체 언어',japanese:'일본어',schinese:'중국어 간체',unknown:'언어 정보 없음'})[evidence.language] || evidence.language;
    const coverage = counts.collected ? ` (${pct(counts.analyzed / counts.collected * 100)})` : '';
    document.getElementById('overviewTitle').textContent = `${V.game?.name || '게임'} 리뷰 진단`;
    document.getElementById('ovCoverage').innerHTML = `<span>${esc(language)} · ${evidence.period ? `${esc(evidence.period.start.replaceAll('-','.'))} – ${esc(evidence.period.end.replaceAll('-','.'))}` : '기간 정보 없음'}</span><span>수집 ${num(counts.collected)}건 · 분석 ${num(counts.analyzed)}건${coverage}</span>`;
    document.getElementById('rdPageArt').innerHTML = V.game?.header_image
      ? `<img src="${esc(V.game.header_image)}" alt="" />` : '<span>게임 이미지 없음</span>';
    document.getElementById('rdPageActions').innerHTML = `<button class="rd-btn" type="button" onclick="startNewAnalysis(${Number(id)},null,null,true)">추가 수집</button><a class="rd-btn" href="/api/reviews/download?app_id=${Number(id)}" download>원문 내려받기</a><a class="rd-btn primary" href="/api/analysis/download?app_id=${Number(id)}" download>분석 결과 내려받기</a>`;
    root.innerHTML = `
      <section class="rd-findings" aria-labelledby="rdFindingsTitle">
        <div class="rd-findings-head"><h2 id="rdFindingsTitle">핵심 인사이트</h2><button class="rd-text-btn rd-method-link" data-action="method">분석 기준</button></div>
        <div class="rd-signals">
          <button class="rd-signal rd-signal-strength" data-action="select" data-theme="${esc(strength?.name || '')}"><span class="rd-signal-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="m4 7 4.2 3.2L12 4l3.8 6.2L20 7l-1.5 10H5.5L4 7Z"/><path d="M6 20h12"/></svg></span><span class="rd-signal-copy"><span class="rd-signal-heading"><strong>${esc(strength?.name || '분석 대기')}</strong><span class="rd-signal-label">긍정 반응 최다</span></span><span class="rd-big">${num(strength?.pos)}<small>건</small></span>${insightBalance(strength)}</span></button>
          <button class="rd-signal rd-signal-concern rd-signal-primary" data-action="select" data-theme="${esc(concern?.name || '')}"><span class="rd-signal-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M13.4 3.2c.5 3-1.5 4.5-3.1 6.3-1.4 1.5-2.3 3-2.3 5.1A5 5 0 0 0 18 15c0-2.7-1.4-5.2-4.6-7.6.2 2-1 3.3-2 4.5"/><path d="M12 20c-1.8 0-3-1.2-3-2.8 0-1.2.7-2.3 2.3-3.5-.1 1.3.8 1.8 1.5 2.4.6.5 1.2 1 1.2 1.9 0 1.1-.8 2-2 2Z"/></svg></span><span class="rd-signal-copy"><span class="rd-signal-heading"><strong>${esc(concern?.name || '뚜렷한 불만 없음')}</strong><span class="rd-signal-label">부정 반응 최다</span></span><span class="rd-big">${num(concern?.neg)}<small>건</small></span>${insightBalance(concern)}</span></button>
          <button class="rd-signal rd-signal-caution" data-action="${small ? 'cohort' : 'recommended'}"><span class="rd-signal-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M10.3 4.2 2.7 18a2 2 0 0 0 1.8 3h15a2 2 0 0 0 1.8-3L13.7 4.2a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4.5M12 17h.01"/></svg></span><span class="rd-signal-copy"><span class="rd-signal-heading"><strong>${esc(small?.label || '추천 속 불만')}</strong><span class="rd-signal-label">${small ? '추가 확인 필요' : '놓치기 쉬운 의견'}</span></span><span class="rd-big">${small ? pct(small.negative_rate) : num(counts.recommended_complaints)}${small ? '' : '<small>건</small>'}</span>${small ? `<span class="rd-mini-bullet" role="img" aria-label="비추천률 ${pct(small.negative_rate)}, 전체 기준 ${pct(evidence.sample_negative_rate)}"><i style="width:${clamp(small.negative_rate)}%"></i><b style="left:${clamp(evidence.sample_negative_rate)}%"></b></span><span class="rd-mini-values"><span>전체 ${pct(evidence.sample_negative_rate)}</span><span>${num(small.negative)} / ${num(small.n)}건 · 표본 적음</span></span>` : '<small>추천 리뷰에도 남은 불만</small>'}</span></button>
        </div>
      </section>
      <div class="rd-main">
        <section class="rd-card" aria-labelledby="rdTopicsTitle">
          <div class="rd-card-head"><div><h2 id="rdTopicsTitle">주제별 반응</h2><p>불만과 칭찬을 같은 축에서 비교합니다.</p></div>
          <div class="rd-toggle" aria-label="주제 정렬"><button data-action="sort" data-sort="negative">불만순</button><button data-action="sort" data-sort="mentions">언급순</button></div></div>
          <div class="rd-chart-key"><span>← 불만</span><span>칭찬 →</span></div><div id="rdTopicChart"></div>
          <div class="rd-chart-footer"><span></span><button class="rd-text-btn" data-action="expand" id="rdExpand">전체 주제</button></div>
        </section>
        <section class="rd-card rd-detail" id="rdDetail" aria-live="polite" aria-label="선택한 주제의 근거"></section>
      </div>
      <div class="rd-lower" id="rdCohorts">
        <section class="rd-card"><div class="rd-card-head"><div><h2>플레이 시간별 비추천 비율</h2><p>작성 당시 플레이 시간 · 전체 ${pct(evidence.sample_negative_rate)}</p></div></div><div id="rdCohortChart"></div>
          ${small ? `<div class="rd-small-note"><b>${esc(small.label)}</b> · ${num(small.negative)} / ${num(small.n)}건 비추천 · 표본 적음</div>` : ''}
        </section>
        <section class="rd-card"><div class="rd-card-head"><div><h2>플레이 구간마다 다른 불만</h2><p>색이 진할수록 해당 구간에서 자주 언급</p></div></div><div id="rdHeatmap"></div><div class="rd-heat-legend">낮음 <i aria-hidden="true"></i> 높음</div></section>
      </div>
      <div class="rd-secondary" id="rdSecondary">
        <section class="rd-card"><div class="rd-card-head"><div><h2>좋아한 경험의 결</h2><p>${num(evidence.fun_denominator)}건 · 복수 선택</p></div></div><div id="rdFun"></div></section>
        <section class="rd-card rd-recommended-card"><div class="rd-card-head"><div><h2>추천 속에도 불만이 있습니다</h2><p>불만 주제가 있는 리뷰 ${num(counts.complaint_reviews)}건</p></div></div><div class="rd-rec-kpi"><strong>${pct(complaintRate)}</strong><span>${num(counts.recommended_complaints)}건이 게임은 추천</span></div><div class="rd-rec-bar" role="img" aria-label="불만 리뷰 ${num(counts.complaint_reviews)}건 중 게임 추천 ${num(counts.recommended_complaints)}건"><i style="width:${clamp(complaintRate)}%"></i></div><div class="rd-rec-legend"><span><i></i>추천 ${num(counts.recommended_complaints)}건</span><span><i></i>비추천 ${num(complaintNotRecommended)}건</span></div></section>
      </div>
      <dialog class="rd-dialog rd-method-dialog" id="rdMethodDialog" aria-labelledby="rdMethodTitle"><div class="rd-dialog-head"><div><h2 id="rdMethodTitle">분석 기준</h2><p>${num(counts.collected)}건 수집 · ${num(counts.analyzed)}건 AI 분석</p></div><button class="rd-btn" data-action="close-method" aria-label="분석 기준 닫기">닫기 ×</button></div><div class="rd-method-grid">
        <p><b>수집 범위</b><br>최신순으로 수집한 리뷰입니다. 추천·비추천 비율을 맞춰도 전체 유저나 전체 기간의 무작위 표본이 되지는 않습니다. 리뷰는 자발적으로 작성한 의견입니다.</p>
        <p><b>비추천 연관 차이</b><br>해당 주제를 언급한 리뷰를 제외했을 때의 추천률 − 전체 수집 추천률입니다. 수집 원자료로 계산하며, 문제 해결 효과나 인과관계를 뜻하지 않습니다. 주제끼리 중복되어 합산할 수 없습니다.</p>
        <p><b>표본과 AI 분류</b><br>주제 수치는 AI가 원문을 분류한 결과입니다. 짧은 리뷰 등 ${num(counts.collected - counts.analyzed)}건은 이 주제 분석에 포함되지 않습니다. 표본 수만으로 AI 분류 정확도나 모집단 오차를 보장하지 않습니다.${counts.skipped_analysis ? ` 읽을 수 없거나 원문이 없는 분석 ${num(counts.skipped_analysis)}건 제외.` : ''}</p>
        <p><b>읽는 순서</b><br>칭찬 많은 경험을 지킬 강점으로 검토하고, 불만의 빈도·비추천 연관·원문을 함께 봅니다. 플레이 구간별 차이는 추가 조사 대상을 찾는 신호입니다. 원문은 공감 수, 최신순으로 보여줍니다.</p>
      </div></dialog>
      <dialog class="rd-dialog" id="rdEvidenceDialog" aria-labelledby="rdDialogTitle"><div class="rd-dialog-head"><div><h2 id="rdDialogTitle">리뷰 근거</h2><p id="rdDialogMeta"></p></div><button class="rd-btn" data-action="close-dialog" aria-label="리뷰 근거 닫기">닫기 ×</button></div><div class="rd-toggle" aria-label="주제 감성 선택"><button data-action="evidence-filter" data-sentiment="N">불만</button><button data-action="evidence-filter" data-sentiment="P">칭찬</button><button data-action="evidence-filter" data-sentiment="all">전체</button></div><div id="rdEvidenceBody" aria-live="polite"></div></dialog>`;
    root.onclick = onClick;
    const dialog = document.getElementById('rdEvidenceDialog');
    dialog.addEventListener('click', event => { if (event.target === dialog) closeDialog(); });
    dialog.addEventListener('close', () => { request?.abort(); restoreFocus?.focus(); });
    const methodDialog = document.getElementById('rdMethodDialog');
    methodDialog.addEventListener('click', event => { if (event.target === methodDialog) closeMethod(); });
    methodDialog.addEventListener('close', () => restoreFocus?.focus());
    renderTopics(); renderDetail(); renderMood(); renderCohorts(); renderHeatmap(); renderFun();
  }

  function renderTopics() {
    const rows = [...evidence.themes].sort((a,b) => sort === 'negative' ? b.neg - a.neg || b.mentions - a.mentions : b.mentions - a.mentions || b.neg - a.neg);
    let visible = expanded ? rows : rows.slice(0,10);
    const chosen = themeByName(selected);
    if (chosen && !visible.includes(chosen) && !expanded) visible = [...visible.slice(0,9), chosen];
    const max = Math.max(10, Math.ceil(Math.max(0, ...evidence.themes.flatMap(t => [t.pos,t.neg])) / 10) * 10);
    const width = value => value / max * 200;
    const tickXs = [40,140,240,340,440];
    document.getElementById('rdTopicChart').innerHTML = visible.map(t => {
      const neg = width(t.neg), pos = width(t.pos);
      return `<button class="rd-topic" data-action="select" data-theme="${esc(t.name)}" aria-pressed="${selected === t.name}" aria-label="${esc(t.name)}, 불만 ${t.neg}건, 칭찬 ${t.pos}건, 원문 확인"><span class="rd-topic-name" title="${esc(t.name)}">${esc(t.name)}</span><svg viewBox="0 0 480 35" aria-hidden="true">${tickXs.map(x => `<line x1="${x}" x2="${x}" y1="0" y2="35" stroke="${x===240?'#b8c3d1':'#edf0f4'}"/>`).join('')}<rect x="${240-neg}" y="10" width="${neg}" height="15" rx="2" fill="${orange}"/><rect x="240" y="10" width="${pos}" height="15" rx="2" fill="${blue}"/><text x="${232-neg}" y="22" text-anchor="end" fill="#C73E4A" font-size="16">${t.neg}</text><text x="${248+pos}" y="22" fill="#1B64DA" font-size="16">${t.pos}</text></svg></button>`;
    }).join('') || '<div class="rd-empty">분류된 주제가 아직 없습니다.</div>';
    if (rows.length) document.getElementById('rdTopicChart').innerHTML += `<svg class="rd-axis" viewBox="0 0 480 25" aria-hidden="true">${[max,max/2,0,max/2,max].map((v,i)=>`<text x="${tickXs[i]}" y="17" text-anchor="middle" font-size="13" fill="#7a8798">${v}</text>`).join('')}</svg>`;
    root.querySelectorAll('[data-action="sort"]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.sort === sort)));
    document.getElementById('rdExpand').textContent = expanded ? '접기 ↑' : `전체 ${rows.length}개 주제 보기 ↓`;
  }

  function renderDetail() {
    const t = themeByName(selected), target = document.getElementById('rdDetail');
    if (!t) { target.innerHTML = '<div class="rd-empty">확인할 주제가 없습니다.</div>'; return; }
    const association = topAssociation(), isAssociation = t.name === association?.name;
    const sentiment = t.neg > t.pos || isAssociation ? 'N' : 'P';
    const definition = data.themes?.find(row => row.name === t.name)?.desc;
    const action = data.actions?.find(row => row.theme === t.name);
    target.innerHTML = `<div class="rd-detail-head"><div><span class="rd-detail-kicker">선택한 주제</span><h2>${esc(t.name)}</h2></div><button class="rd-text-btn rd-evidence-link" data-action="evidence" data-sentiment="${sentiment}">리뷰 근거 →</button></div><p class="rd-desc">${esc(definition || '칭찬과 불만을 함께 살펴보세요.')}</p>
      <div class="rd-detail-metrics"><div><strong>${num(t.neg)}<small>건</small></strong><span>불만</span></div><div><strong>${num(t.pos)}<small>건</small></strong><span>칭찬</span></div><div><strong style="font-size:22px">${signed(t.exclusion_delta)}</strong><span>추천률 연관 차이</span></div></div>
      ${action?.prob ? `<div class="rd-problem-summary"><b>핵심 문제</b><p>${esc(action.prob)}</p></div>` : ''}
      ${t.neg ? `<span class="rd-inline-note">불만 중 게임 추천 <b>${num(t.negative_recommended)} / ${num(t.neg)}건</b></span>` : '<span class="rd-inline-note">이 주제의 불만은 발견되지 않았습니다.</span>'}
      ${action ? `<details class="rd-ai-detail"><summary>원인과 개선 제안</summary>${action.why?`<p><b>리뷰에서 언급된 원인</b><br>${esc(action.why)}</p>`:''}${action.fix?.length?`<p><b>리뷰에서 추출한 제안</b><br>${action.fix.map(esc).join(' · ')}</p>`:''}<p class="rd-caption">AI 요약에는 잘못된 연결이 포함될 수 있습니다. 원문 확인 후 기획에 반영하세요.</p></details>`:''}`;
  }

  function renderMood() {
    const mood = evidence.mood || {};
    const groups = [
      {key:'P', label:'긍정', cls:'positive'},
      {key:'M', label:'혼합', cls:'mixed'},
      {key:'N', label:'부정', cls:'negative'},
      {key:'U', label:'판단 어려움', cls:'unknown'}
    ];
    const total = groups.reduce((n,g) => n + (Number(mood[g.key]) || 0), 0);
    const target = document.getElementById('rdMoodChart');
    if (!total) {
      target.innerHTML = '<p class="rd-caption">분류된 리뷰가 없습니다.</p>';
      document.getElementById('rdHeaderVerdict').innerHTML = '<div><strong>반응 분포를 판단할 자료가 없습니다.</strong><p>분석을 완료하면 이곳에 핵심 결론이 표시됩니다.</p></div>';
      return;
    }
    const visible = groups.filter(g => Number(mood[g.key]) > 0);
    const colors = {P:'#3182F6', M:'#8BB7F5', N:'#F04452', U:'#AEB8C6'};
    const radius = 52, circumference = 2 * Math.PI * radius, gap = 2.2;
    let cursor = 0;
    const rings = visible.map(g => {
      const length = Number(mood[g.key]) / total * circumference;
      const ring = `<circle cx="70" cy="70" r="${radius}" fill="none" stroke="${colors[g.key]}" stroke-width="22" stroke-dasharray="${Math.max(0,length-gap)} ${circumference}" stroke-dashoffset="${-cursor}"/>`;
      cursor += length;
      return ring;
    }).join('');
    const leading = visible.reduce((a,b) => Number(mood[a.key]) >= Number(mood[b.key]) ? a : b);
    const leadingRate = Math.max(...visible.map(g => Number(mood[g.key]))) / total * 100;
    const rates = Object.fromEntries(groups.map(g => [g.key, Number(mood[g.key] || 0) / total * 100]));
    target.innerHTML = `<div class="rd-mood-visual">
      <div class="rd-mood-donut" role="img" aria-label="${visible.map(g => `${g.label} ${num(mood[g.key])}건`).join(', ')}"><svg viewBox="0 0 140 140" aria-hidden="true"><g transform="rotate(-90 70 70)">${rings}</g></svg><div><strong>${num(total)}</strong><small>분석 건수</small></div></div>
      <div class="rd-mood-key">${visible.map(g => `<span><i class="${g.cls}"></i><b>${g.label}</b><strong>${pct(mood[g.key] / total * 100)}</strong><small>${num(mood[g.key])}건</small></span>`).join('')}</div>
    </div>`;
    let verdictTitle, verdictBody;
    if (rates.P >= 70) {
      verdictTitle = '대체로 긍정적인 반응이 많은 게임입니다.';
      verdictBody = `분석한 리뷰의 ${pct(rates.P)}가 긍정 반응으로 분류되어, 전반적인 평가가 양호합니다.`;
    } else if (rates.P >= 55) {
      verdictTitle = '긍정적인 반응이 다소 우세한 게임입니다.';
      verdictBody = `긍정 반응이 ${pct(rates.P)}로 절반을 넘지만, 부정과 혼합 반응도 함께 확인할 필요가 있습니다.`;
    } else if (rates.N >= 40) {
      verdictTitle = '부정적인 반응을 먼저 살펴볼 필요가 있습니다.';
      verdictBody = `분석한 리뷰의 ${pct(rates.N)}가 부정 반응으로 분류됐습니다. 반복해서 언급된 문제부터 확인하세요.`;
    } else {
      verdictTitle = '긍정과 부정이 함께 나타나는 게임입니다.';
      verdictBody = `가장 큰 반응은 ${leading.label} ${pct(leadingRate)}이며, 한쪽 평가만으로 전체 반응을 설명하기 어렵습니다.`;
    }
    document.getElementById('rdHeaderVerdict').innerHTML = `<span class="rd-verdict-icon" aria-hidden="true"><i></i><i></i><i></i></span><div><strong>${verdictTitle}</strong><p>${verdictBody}</p></div>`;
  }

  function renderCohorts() {
    const base = evidence.sample_negative_rate;
    const rows = evidence.cohorts.filter(c => c.n > 0);
    if (!rows.length) { document.getElementById('rdCohortChart').innerHTML = '<div class="rd-empty">작성 당시 플레이 시간이 있는 리뷰가 없습니다.</div>'; return; }
    document.getElementById('rdCohortChart').innerHTML = rows.map(c => `<div class="rd-cohort-row ${c.small && c.n ? 'small' : ''}">
      <div class="rd-cohort-label"><strong>${esc(c.label)}</strong><small>${num(c.n)}건${c.small && c.n ? ' · 표본 적음' : ''}</small></div>
      <div class="rd-cohort-track" role="img" aria-label="${esc(c.label)}, ${num(c.n)}건 중 비추천 ${num(c.negative)}건, ${pct(c.negative_rate)}">
        ${base == null ? '' : `<i class="rd-cohort-base" style="left:${clamp(base)}%"></i>`}
        ${c.negative_rate == null ? '' : `<i class="rd-cohort-fill" style="width:${clamp(c.negative_rate)}%"></i>`}
      </div><strong class="rd-cohort-rate">${pct(c.negative_rate)}</strong></div>`).join('') +
      `<p class="rd-cohort-legend">점선: 수집 리뷰 전체 비추천율 ${pct(base)}</p>`;
  }

  function renderHeatmap() {
    const rows = [...evidence.themes].sort((a,b)=>b.neg-a.neg).filter(t=>t.neg>0).slice(0,5);
    if (!rows.length) { document.getElementById('rdHeatmap').innerHTML = '<div class="rd-empty">분류된 불만 주제가 없습니다.</div>'; return; }
    const max = Math.max(1,...rows.flatMap(t=>t.cells.filter(c=>c.denominator>=30).map(c=>c.rate||0)));
    document.getElementById('rdHeatmap').innerHTML = `<table class="rd-heatmap"><thead><tr><th scope="col">주제</th>${evidence.cohorts.map(c=>`<th scope="col">${esc(c.label)}<br><span>${num(c.analyzed)}건 분석</span></th>`).join('')}</tr></thead><tbody>${rows.map(t=>`<tr><th scope="row">${esc(t.name)}<\/th>${t.cells.map(c=>{const uncertain=c.denominator<30; const intensity=c.rate==null?0:Math.min(1,c.rate/max); const alpha=c.count?0.1+intensity*0.75:0.025;return `<td class="${c.denominator<30?'small':''}"><button data-action="select-scroll" data-theme="${esc(t.name)}" style="background:${uncertain?'#F2F4F6':`rgba(240,68,82,${alpha})`};color:${!uncertain && intensity>.65?'#fff':'#6B7684'}" aria-label="${esc(t.name)}, ${num(c.denominator)}건 분석 중 불만 ${num(c.count)}건, ${pct(c.rate)}, 주제 근거 보기" title="${num(c.count)} / ${num(c.denominator)}건 (${pct(c.rate)})">${c.denominator?num(c.count):'—'}</button></td>`;}).join('')}</tr>`).join('')}</tbody></table>`;
  }

  function renderFun() {
    document.getElementById('rdFun').innerHTML = evidence.fun.slice(0,4).map(f=>`<div class="rd-fun-row" title="${esc(f.desc)} · ${num(f.count)} / ${num(evidence.fun_denominator)}건"><span>${esc(f.name)}</span><div class="rd-fun-track"><i style="width:${clamp(f.share)}%"></i></div><strong>${pct(f.share)}</strong></div>`).join('') || '<div class="rd-empty">재미 분류가 없습니다.</div>';
  }

  function scrollToPanel(id) {
    document.getElementById(id)?.scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
  }
  function onClick(event) {
    const button = event.target.closest('[data-action]');
    if (!button) return;
    const action = button.dataset.action;
    if (action === 'select' || action === 'select-scroll') {
      if (!themeByName(button.dataset.theme)) return;
      selected = button.dataset.theme; updateURL(); renderTopics(); renderDetail();
      if (action === 'select-scroll' || (button.classList.contains('rd-signal') && innerWidth<1080)) scrollToPanel('rdDetail');
    } else if (action === 'sort') { sort=button.dataset.sort; updateURL(); renderTopics(); }
    else if (action === 'expand') { expanded=!expanded; renderTopics(); }
    else if (action === 'cohort') scrollToPanel('rdCohorts');
    else if (action === 'recommended') scrollToPanel('rdSecondary');
    else if (action === 'collect') window.startNewAnalysis(appId,null,null,true);
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
