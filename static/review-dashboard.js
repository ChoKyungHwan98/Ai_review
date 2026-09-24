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
    const language = ({koreana:'한국어',english:'영어',all:'전체 언어',japanese:'일본어',schinese:'중국어 간체',unknown:'언어 정보 없음'})[evidence.language] || evidence.language;
    document.getElementById('overviewTitle').textContent = `${V.game?.name || '게임'} 리뷰 진단`;
    document.getElementById('ovCoverage').textContent = `${language} · ${evidence.period ? `${evidence.period.start.replaceAll('-','.')} – ${evidence.period.end.replaceAll('-','.')}` : '기간 정보 없음'} · 수집 ${num(counts.collected)}건 / AI 분석 ${num(counts.analyzed)}건`;
    root.innerHTML = `
      <div class="rd-toolbar">
        <div class="rd-tools"><button class="rd-btn" data-action="collect">추가 수집</button><a class="rd-btn" href="/api/reviews/download?app_id=${appId}" download>원문 CSV</a><a class="rd-btn" href="/api/analysis/download?app_id=${appId}" download>분석 CSV ↓</a></div></div>
      <div class="rd-signals">
        <button class="rd-signal" data-action="select" data-theme="${esc(strength?.name || '')}"><span class="rd-eyebrow">긍정 반응 최다</span><strong>${esc(strength?.name || '분석 대기')}</strong><span class="rd-big">${num(strength?.pos)}<small>건</small></span><small>칭찬이 가장 많이 모인 주제</small></button>
        <button class="rd-signal rd-signal-concern" data-action="select" data-theme="${esc(concern?.name || '')}"><span class="rd-eyebrow">부정 반응 최다</span><strong>${esc(concern?.name || '뚜렷한 불만 없음')}</strong><span class="rd-big">${num(concern?.neg)}<small>건</small></span><small>${concern ? '불만이 가장 많이 모인 주제' : '원문이 쌓이면 다시 확인하세요'}</small></button>
        <button class="rd-signal" data-action="${small ? 'cohort' : 'recommended'}"><span class="rd-eyebrow">${small ? '추가 확인 필요' : '놓치기 쉬운 의견'}</span><strong>${esc(small?.label || '추천 속 불만')}</strong><span class="rd-big">${num(small?.n ?? counts.recommended_complaints)}<small>건</small></span><small>${small ? `비추천 ${num(small.negative)} / ${num(small.n)}건 · 판단 보류` : counts.recommended_complaints ? '추천 리뷰에도 불만이 있습니다' : '이번 자료에서는 발견되지 않았습니다'}</small></button>
      </div>
      <section class="rd-mood rd-card" aria-labelledby="rdMoodTitle">
        <div class="rd-mood-intro"><h2 id="rdMoodTitle">리뷰 감정 분포</h2><p>분석 ${num(counts.analyzed)}건 · 추천 여부와 별개</p></div>
        <div id="rdMoodChart"></div>
      </section>
      <div class="rd-main">
        <section class="rd-card" aria-labelledby="rdTopicsTitle">
          <div class="rd-card-head"><div><h2 id="rdTopicsTitle">주제별 반응</h2><p>AI 분석 ${num(counts.analyzed)}건 · 주제별 리뷰 수</p></div>
          <div class="rd-toggle" aria-label="주제 정렬"><button data-action="sort" data-sort="negative">불만순</button><button data-action="sort" data-sort="mentions">언급순</button></div></div>
          <div class="rd-chart-key"><span>← 불만</span><span>칭찬 →</span></div><div id="rdTopicChart"></div>
          <div class="rd-chart-footer"><p class="rd-caption">같은 축 · 한 리뷰에서 칭찬과 불만을 함께 셀 수 있음</p><button class="rd-text-btn" data-action="expand" id="rdExpand">전체 주제</button></div>
        </section>
        <section class="rd-card rd-detail" id="rdDetail" aria-live="polite" aria-label="선택한 주제의 근거"></section>
      </div>
      <div class="rd-lower" id="rdCohorts">
        <section class="rd-card"><div class="rd-card-head"><div><h2>플레이 시간별 비추천 비율</h2><p>작성 당시 플레이 시간 기준 · 전체 ${pct(evidence.sample_negative_rate)}</p></div></div><div id="rdCohortChart"></div>
          ${small ? `<div class="rd-small-note">${esc(small.label)}은 비추천 ${num(small.negative)} / ${num(small.n)}건. 표본이 적어 판단을 보류합니다.</div>` : ''}
          <p class="rd-caption">각 구간은 서로 다른 리뷰 작성자입니다. 유저 이탈률이나 시간이 흐른 뒤의 만족도 변화가 아닙니다.${counts.unknown_playtime ? ` 작성 시 플레이 시간 미상 ${num(counts.unknown_playtime)}건 제외.` : ''}</p>
        </section>
        <section class="rd-card"><div class="rd-card-head"><div><h2>플레이 구간마다 다른 불만</h2><p>셀 안 숫자 = 불만 리뷰 수 · 색 농도 = 해당 구간 AI 분석 대비 비율</p></div></div><div id="rdHeatmap"></div><div class="rd-heat-legend">구간 내 불만 비율 낮음 <i aria-hidden="true"></i> 높음</div><p class="rd-caption">추천 리뷰 속 불만도 포함 · 점선 열은 AI 분석 30건 미만으로 색상 비교에서 제외</p></section>
      </div>
      <div class="rd-secondary" id="rdSecondary">
        <section class="rd-card"><div class="rd-card-head"><div><h2>좋아한 경험의 결</h2><p>긍정·혼합으로 분류된 ${num(evidence.fun_denominator)}건의 재미 언급 · 복수 분류</p></div></div><div id="rdFun"></div><p class="rd-caption">한 리뷰에 여러 재미가 담길 수 있어 비율의 합은 100%를 넘을 수 있습니다.</p></section>
        <section class="rd-card"><div class="rd-card-head"><div><h2>추천해도 불만은 남깁니다</h2><p>주제별 불만이 있는 ${num(counts.complaint_reviews)}건 중</p></div></div><div class="rd-detail-metrics"><div><strong>${num(counts.recommended_complaints)}<small>건</small></strong><span>게임은 추천, 일부 경험은 불만</span></div><div><strong>${counts.complaint_reviews ? pct(counts.recommended_complaints / counts.complaint_reviews * 100) : '—'}</strong><span>불만 리뷰 중 추천 비중</span></div></div><p class="rd-caption">비추천 리뷰만 읽으면 이 의견을 놓칩니다. 칭찬과 불만은 게임 전체의 추천 여부와 별도로 분석했습니다.</p><div class="rd-periods"><div class="rd-period"><span>스팀 조회 추천률</span><strong>${pct(V.rates?.steam)}</strong><span>조회 조건 기준</span></div><div class="rd-period"><span>수집 리뷰 추천률</span><strong>${evidence.sample_negative_rate == null ? '—' : pct(100 - evidence.sample_negative_rate)}</strong><span>${num(counts.collected)}건 기준</span></div></div></section>
      </div>
      <details class="rd-method" id="rdMethod"><summary>분석 범위와 읽는 법 · ${num(counts.analyzed)}건의 AI 분류, 원문 검증 필요</summary><div class="rd-method-grid">
        <p><b>수집 범위</b><br>최신순으로 수집한 리뷰입니다. 추천·비추천 비율을 맞춰도 전체 유저나 전체 기간의 무작위 표본이 되지는 않습니다. 리뷰는 자발적으로 작성한 의견입니다.</p>
        <p><b>비추천 연관 차이</b><br>해당 주제를 언급한 리뷰를 제외했을 때의 추천률 − 전체 수집 추천률입니다. 수집 원자료로 계산하며, 문제 해결 효과나 인과관계를 뜻하지 않습니다. 주제끼리 중복되어 합산할 수 없습니다.</p>
        <p><b>표본과 AI 분류</b><br>주제 수치는 AI가 원문을 분류한 결과입니다. 짧은 리뷰 등 ${num(counts.collected - counts.analyzed)}건은 이 주제 분석에 포함되지 않습니다. 표본 수만으로 AI 분류 정확도나 모집단 오차를 보장하지 않습니다.${counts.skipped_analysis ? ` 읽을 수 없거나 원문이 없는 분석 ${num(counts.skipped_analysis)}건 제외.` : ''}</p>
        <p><b>읽는 순서</b><br>칭찬 많은 경험을 지킬 강점으로 검토하고, 불만의 빈도·비추천 연관·원문을 함께 봅니다. 플레이 구간별 차이는 추가 조사 대상을 찾는 신호입니다. 원문은 공감 수, 최신순으로 보여줍니다.</p>
      </div></details>
      <dialog class="rd-dialog" id="rdEvidenceDialog" aria-labelledby="rdDialogTitle"><div class="rd-dialog-head"><div><h2 id="rdDialogTitle">리뷰 근거</h2><p id="rdDialogMeta"></p></div><button class="rd-btn" data-action="close-dialog" aria-label="리뷰 근거 닫기">닫기 ×</button></div><div class="rd-toggle" aria-label="주제 감성 선택"><button data-action="evidence-filter" data-sentiment="N">불만</button><button data-action="evidence-filter" data-sentiment="P">칭찬</button><button data-action="evidence-filter" data-sentiment="all">전체</button></div><div id="rdEvidenceBody" aria-live="polite"></div></dialog>`;
    root.onclick = onClick;
    const dialog = document.getElementById('rdEvidenceDialog');
    dialog.addEventListener('click', event => { if (event.target === dialog) closeDialog(); });
    dialog.addEventListener('close', () => { request?.abort(); restoreFocus?.focus(); });
    renderTopics(); renderDetail(); renderMood(); renderCohorts(); renderHeatmap(); renderFun();
  }

  function renderTopics() {
    const rows = [...evidence.themes].sort((a,b) => sort === 'negative' ? b.neg - a.neg || b.mentions - a.mentions : b.mentions - a.mentions || b.neg - a.neg);
    let visible = expanded ? rows : rows.slice(0,8);
    const chosen = themeByName(selected);
    if (chosen && !visible.includes(chosen) && !expanded) visible = [...visible.slice(0,7), chosen];
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
    const example = t.examples[sentiment][0];
    const definition = data.themes?.find(row => row.name === t.name)?.desc;
    const action = data.actions?.find(row => row.theme === t.name);
    target.innerHTML = `<span class="rd-eyebrow">${isAssociation ? '비추천과의 연관 차이가 큰 주제' : '선택한 주제 · 원문으로 확인'}</span><h2>${esc(t.name)}</h2><p class="rd-desc">${esc(definition || '칭찬과 불만을 함께 살펴보세요.')}</p>
      <div class="rd-detail-metrics"><div><strong>${num(t.neg)}<small>건</small></strong><span>불만 리뷰</span></div><div><strong>${num(t.pos)}<small>건</small></strong><span>칭찬 리뷰</span></div><div><strong style="font-size:22px">${signed(t.exclusion_delta)}</strong><span>주제 제외 시 추천률 차이</span></div></div>
      <p class="rd-caption">관찰된 연관 차이입니다. 이 문제를 고쳤을 때의 상승 예상치는 아닙니다.</p>
      ${example ? `<blockquote class="rd-quote"><p>“${esc(example.content)}${example.truncated?'…':''}”</p><footer>${sentiment==='N'?'불만':'칭찬'}으로 분류 · ${example.recommended?'게임 추천':'게임 비추천'} · ${example.hours==null?'시간 미상':`${num(Math.round(example.hours))}시간`}</footer></blockquote>` : '<p class="rd-caption">연결된 원문이 없습니다.</p>'}
      ${t.neg ? `<span class="rd-inline-note">불만 ${num(t.neg)}건 중 <b>${num(t.negative_recommended)}건은 게임을 추천</b>했습니다.</span>` : '<span class="rd-inline-note">현재 분석에서 이 주제의 불만은 발견되지 않았습니다.</span>'}
      <div class="rd-detail-actions"><button class="rd-btn primary" data-action="evidence" data-sentiment="${sentiment}">원문 ${sentiment==='N'?'불만':'칭찬'} ${num(t[sentiment==='N'?'neg':'pos'])}건 보기 →</button><button class="rd-btn" data-action="evidence" data-sentiment="all">전체 근거</button></div>
      ${action ? `<details class="rd-ai-detail"><summary>AI가 정리한 문제와 제안</summary><p><b>경험한 문제</b><br>${esc(action.prob || '정리된 문제 없음')}</p>${action.why?`<p><b>AI가 정리한 원인 추정</b><br>${esc(action.why)}</p>`:''}${action.fix?.length?`<p><b>리뷰에서 추출한 제안</b><br>${action.fix.map(esc).join(' · ')}</p>`:''}<p class="rd-caption">AI 요약에는 추정이나 잘못된 연결이 포함될 수 있습니다. 원문 확인 후 기획에 반영하세요.</p></details>`:''}`;
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
    if (!total) { target.innerHTML = '<p class="rd-caption">분류된 리뷰가 없습니다.</p>'; return; }
    const visible = groups.filter(g => Number(mood[g.key]) > 0);
    const colors = {P:'#3182F6', M:'#83B3F5', N:'#F04452', U:'#B0B8C1'};
    let cursor = 0;
    const slices = visible.map(g => {
      const start = cursor;
      cursor += Number(mood[g.key]) / total * 100;
      return `${colors[g.key]} ${start.toFixed(3)}% ${cursor.toFixed(3)}%`;
    });
    target.innerHTML = `<div class="rd-mood-visual">
      <div class="rd-mood-donut" role="img" aria-label="${visible.map(g => `${g.label} ${num(mood[g.key])}건`).join(', ')}" style="background:conic-gradient(${slices.join(',')})"><div><strong>${num(total)}</strong><small>분석 건수</small></div></div>
      <div class="rd-mood-key">${visible.map(g => `<span><i class="${g.cls}"></i><b>${g.label}</b><strong>${pct(mood[g.key] / total * 100)}</strong><small>${num(mood[g.key])}건</small></span>`).join('')}</div>
    </div>`;
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
    else if (action === 'evidence') {
      restoreFocus = button; dialogTheme=selected; dialogSentiment=button.dataset.sentiment; dialogPage=1;
      document.getElementById('rdEvidenceDialog').showModal(); loadEvidence();
    } else if (action === 'close-dialog') closeDialog();
    else if (action === 'evidence-filter') { dialogSentiment=button.dataset.sentiment; dialogPage=1; loadEvidence(); }
    else if (action === 'evidence-page') { dialogPage=Number(button.dataset.page); loadEvidence(); }
    else if (action === 'retry-evidence') loadEvidence();
  }
  function closeDialog() { document.getElementById('rdEvidenceDialog').close(); }
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
