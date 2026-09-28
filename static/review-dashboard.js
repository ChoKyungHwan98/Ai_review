/* 리뷰 진단 화면. 한 문장 결론 → 주제별 칭찬·불만 차트 → 선택 주제 근거 → 플레이 시간.
   모든 막대와 문장은 현재 게임의 evidence 집계로만 그린다. 설계 규칙은 AGENTS.md 참고. */
window.ReviewDashboard = (() => {
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = x => x == null ? '—' : Number(x).toLocaleString('ko-KR');
  const pct = x => x == null ? '—' : `${Number(x).toFixed(1)}%`;
  const clamp = x => Math.max(0, Math.min(100, Number(x) || 0));
  const COLLAPSED_ROWS = 10, MAX_CONCERN_ROWS = 4;
  const ICONS = {
    plus: '<path d="M12 5v14M5 12h14"/>',
    report: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
    download: '<path d="M12 3v12M7 10l5 5 5-5M4 19h16"/>',
    review: '<path d="M20 15a2 2 0 0 1-2 2H8l-4 4V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2z"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>'
  };
  const icon = name => `<svg class="rd-icon" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name]}</svg>`;
  let data, evidence, appId, root, selected, expanded = false, view = 'map', resizeBound = false;
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
    document.getElementById('rdPageActions').innerHTML = `<button class="rd-btn" type="button" onclick="startNewAnalysis(${Number(id)},null,null,true)">${icon('plus')}추가 수집</button><a class="rd-btn" href="/api/reviews/download?app_id=${Number(id)}" download>${icon('download')}원문</a><a class="rd-btn" href="/api/analysis/download?app_id=${Number(id)}" download>${icon('download')}분석 결과</a><button class="rd-btn primary" type="button" onclick="ReviewDashboard.report()">${icon('report')}한 장 보고서</button>`;
    if (!evidence) {
      document.getElementById('overviewTitle').textContent = `${V.game?.name || '게임'} 리뷰 진단`;
      document.getElementById('ovCoverage').textContent = '';
      root.innerHTML = '<div class="rd-card rd-empty">이 분석에는 원문 연결 데이터가 없습니다. 추가 분석 후 주제별 근거를 확인할 수 있습니다.</div>';
      return;
    }
    const counts = evidence.counts;
    const language = ({koreana:'한국어',english:'영어',all:'모든 언어',japanese:'일본어',schinese:'중국어 간체',tchinese:'중국어 번체',unknown:'언어 정보 없음'})[evidence.language] || evidence.language;
    const period = evidence.period ? `${evidence.period.start.replaceAll('-','.')} – ${evidence.period.end.replaceAll('-','.')}` : '기간 정보 없음';
    document.getElementById('overviewTitle').innerHTML = verdictHTML();
    const summary = document.getElementById('ovSummary');
    if (summary) summary.innerHTML = V.summary ? `<b>${V.summary_source === 'rule' ? '요약' : 'AI 요약'}</b><span>${esc(V.summary)}</span>` : '';
    document.getElementById('ovCoverage').innerHTML = `<span>${esc(V.game?.name || '게임')}</span><span>${esc(language)} Steam 리뷰</span><span>${esc(period)}</span><span>AI 분석 ${num(counts.analyzed)}건 / 수집 ${num(counts.collected)}건</span>`;

    const params = new URLSearchParams(location.search);
    selected = themeByName(params.get('topic'))?.name || concern()?.name || strength()?.name || evidence.themes[0]?.name;
    expanded = false;
    view = params.get('view') === 'bars' ? 'bars' : 'map';
    root.innerHTML = `
      <div class="rd-bench">
        <section class="rd-pane rd-pane-chart" aria-labelledby="rdTopicsTitle">
          <header class="rd-pane-head">
            <div><h2 id="rdTopicsTitle"></h2><p id="rdTopicsNote"></p></div>
            <div class="rd-toggle" aria-label="차트 보기"><button data-action="view" data-view="map">IPA 매트릭스</button><button data-action="view" data-view="bars">칭찬·불만 막대</button></div>
          </header>
          <div class="rd-pane-body" id="rdTopicChart"></div>
          <footer class="rd-pane-foot">
            <span>한 리뷰가 여러 주제에 들어갈 수 있습니다</span>
            <button class="rd-text-btn" data-action="method">${icon('info')}분석 기준</button>
          </footer>
        </section>
        <aside class="rd-pane rd-focus" id="rdDetail" aria-live="polite" aria-label="선택한 주제의 근거"></aside>
      </div>
      <div class="rd-bench rd-bench-lower">
        <section class="rd-pane" aria-labelledby="rdWhenTitle">
          <header class="rd-pane-head"><div><h2 id="rdWhenTitle">플레이 시간별 비추천율</h2><p>수집 리뷰 ${num(counts.collected)}건 · 작성 당시 플레이 시간 · 점선은 전체 ${pct(evidence.sample_negative_rate)}</p></div></header>
          <div class="rd-pane-body" id="rdCohortChart"></div>
        </section>
        <section class="rd-pane" aria-labelledby="rdFunTitle">
          <header class="rd-pane-head"><div><h2 id="rdFunTitle">플레이어가 즐긴 것</h2><p>긍정·혼합 리뷰 ${num(evidence.fun_denominator)}건 · 한 리뷰에 여러 개 가능</p></div></header>
          <div class="rd-pane-body" id="rdFunChart"></div>
        </section>
      </div>
      <dialog class="rd-dialog rd-method-dialog" id="rdMethodDialog" aria-labelledby="rdMethodTitle"><div class="rd-dialog-head"><div><h2 id="rdMethodTitle">분석 기준</h2><p>${num(counts.collected)}건 수집 · ${num(counts.analyzed)}건 AI 분석</p></div><button class="rd-btn" data-action="close-method" aria-label="분석 기준 닫기">닫기 ×</button></div><div class="rd-method-grid">
        <p><b>IPA 매트릭스</b><br>중요도–성과 분석(Importance–Performance Analysis)입니다. 가로축은 주제를 언급한 AI 분석 리뷰 수(칭찬+불만)로 중요도를, 세로축은 그중 불만 비율로 성과의 부족을 나타냅니다. 원 크기도 언급 수입니다. 세로 점선은 전체 주제의 언급 수 중앙값, 가로 점선은 불만 50%입니다. 언급 수가 네 배 이상 차이 나면 가로축을 로그 눈금으로 그려 같은 간격이 같은 배율을 뜻합니다. 네 영역은 중점투자(많이 언급 · 불만 우세), 유지강화(많이 언급 · 칭찬 우세), 점진적 개선(적게 언급 · 불만 우세), 현상유지(적게 언급 · 칭찬 우세)입니다.</p>
        <p><b>칭찬·불만 막대</b><br>막대 길이는 해당 주제를 칭찬하거나 불만으로 언급한 AI 분석 리뷰 수입니다. 양쪽이 같은 눈금을 씁니다. 칭찬이 더 많은 주제는 위에서 칭찬순, 불만이 더 많은 주제는 아래 구역에서 불만순으로 놓입니다.</p>
        <p><b>지킬 것 · 고칠 것</b><br>지킬 것은 칭찬이 더 많은 주제 중 칭찬 리뷰가 가장 많은 주제, 고칠 것은 불만이 더 많은 주제 중 불만 리뷰가 가장 많은 주제입니다. 조사를 시작할 곳이지 개선 효과나 우선순위를 증명하지 않습니다.</p>
        <p><b>수집 범위</b><br>최신순으로 수집한 리뷰입니다. 추천·비추천 비율을 맞춰도 전체 유저나 전체 기간의 무작위 표본이 되지는 않습니다. 리뷰는 자발적으로 작성한 의견입니다.</p>
        <p><b>표본과 AI 분류</b><br>주제 수치는 AI가 원문을 분류한 결과입니다. 짧은 리뷰 등 ${num(counts.collected - counts.analyzed)}건은 주제 분석에 포함되지 않습니다. 플레이 시간별 비추천율은 수집 리뷰 전체의 Steam 추천 여부로 계산합니다.${counts.skipped_analysis ? ` 읽을 수 없거나 원문이 없는 분석 ${num(counts.skipped_analysis)}건 제외.` : ''}${evidence.merges?.length ? ` AI가 나눈 주제 중 같은 리뷰에 80% 이상 함께 붙은 ${num(evidence.merges.length)}개는 규칙으로 합쳤습니다(분석 설계 참고).` : ''}</p>
      </div></dialog>
      <dialog class="rd-dialog" id="rdEvidenceDialog" aria-labelledby="rdDialogTitle"><div class="rd-dialog-head"><div><h2 id="rdDialogTitle">리뷰 근거</h2><p id="rdDialogMeta"></p></div><button class="rd-btn" data-action="close-dialog" aria-label="리뷰 근거 닫기">닫기 ×</button></div><div class="rd-toggle" aria-label="주제 감성 선택"><button data-action="evidence-filter" data-sentiment="N">불만</button><button data-action="evidence-filter" data-sentiment="P">칭찬</button><button data-action="evidence-filter" data-sentiment="all">전체</button></div><div id="rdEvidenceBody" aria-live="polite"></div></dialog>`;
    root.onclick = onClick;
    const dialog = document.getElementById('rdEvidenceDialog');
    dialog.addEventListener('click', event => { if (event.target === dialog) closeDialog(); });
    dialog.addEventListener('close', () => { request?.abort(); restoreFocus?.focus(); });
    const methodDialog = document.getElementById('rdMethodDialog');
    methodDialog.addEventListener('click', event => { if (event.target === methodDialog) closeMethod(); });
    methodDialog.addEventListener('close', () => restoreFocus?.focus());
    root.onkeydown = event => {
      if ((event.key === 'Enter' || event.key === ' ') && event.target.matches?.('.rd-dot')) { event.preventDefault(); event.target.dispatchEvent(new MouseEvent('click', {bubbles:true})); }
    };
    if (!resizeBound) {
      resizeBound = true;
      let timer;
      addEventListener('resize', () => { clearTimeout(timer); timer = setTimeout(() => { if (view === 'map' && document.getElementById('rdTopicChart')) renderChart(); }, 150); });
    }
    renderChart(); renderDetail(); renderCohorts(); renderFun();
  }

  function renderChart() {
    const title = {map:'IPA 매트릭스', bars:'주제별 칭찬과 불만'}[view];
    const note = {map: innerWidth < 560 ? '언급량 × 불만 비율 · 원을 누르면 근거' : `언급량 × 불만 비율 · AI 분석 리뷰 ${num(evidence.counts.analyzed)}건 · 원을 누르면 근거가 나옵니다`, bars:`AI 분석 리뷰 ${num(evidence.counts.analyzed)}건 · 주제를 누르면 근거가 나옵니다`}[view];
    document.getElementById('rdTopicsTitle').textContent = title;
    document.getElementById('rdTopicsNote').textContent = note;
    root.querySelectorAll('[data-action="view"]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.view === view)));
    if (view === 'map') renderMap(); else renderTopics();
  }

  // IPA 매트릭스: x = 언급 수, y = 불만 비율, 원 크기 = 언급 수. 점선은 언급 수 중앙값과 불만 50%.
  let mapObserver;
  function renderMap() {
    const target = document.getElementById('rdTopicChart');
    // 높이: 첫 화면 안에 차트 전체가 들어오게(설계 원칙 1). 큰 화면에서는 남는 높이를 채우되 640px까지.
    const W = Math.max(300, target.clientWidth || 800);
    const scroller = document.querySelector('.main-wrap');
    const top = target.getBoundingClientRect().top + (scroller?.scrollTop || 0);
    const room = innerHeight - top - 76;
    const H = W < 480 ? 320 : Math.round(Math.max(300, Math.min(640, room, W * .62)));
    target.innerHTML = mapSVG(W, H) || '<div class="rd-empty">분류된 주제가 아직 없습니다.</div>';
    target.dataset.mapWidth = W;
    // 처음 그릴 때 화면이 아직 숨겨져 있으면 폭을 모른다. 실제 폭이 정해지면 그 폭에 맞춰 다시 그린다.
    if (window.ResizeObserver) {
      mapObserver?.disconnect();
      mapObserver = new ResizeObserver(() => {
        const w = target.clientWidth;
        if (view === 'map' && w && Math.abs(Math.max(300, w) - Number(target.dataset.mapWidth)) > 24) renderMap();
      });
      mapObserver.observe(target);
    }
  }

  // IPA 매트릭스 SVG 문자열. 화면과 한 장 보고서가 같은 그림을 쓴다.
  // 가로 = 언급 수(중요도), 세로 = 불만 비율(성과의 반대). 기준선은 언급 수 중앙값과 불만 50%.
  function mapSVG(W, H) {
    const topics = evidence.themes.filter(t => t.mentions > 0);
    if (!topics.length) return '';
    const mentions = topics.map(t => t.mentions);
    const maxM = Math.max(...mentions), minM = Math.min(...mentions);
    // 언급 수가 네 배 이상 벌어지면 로그 눈금. 선형이면 적게 언급된 주제가 왼쪽 끝에 몰린다.
    const logScale = maxM / minM >= 4;
    const L = 40, R = 12, T = 16, B = logScale ? (W < 480 ? 40 : 46) : 30, pw = W - L - R, ph = H - T - B;
    const sorted = [...mentions].sort((a,b) => a - b);
    const median = sorted.length % 2 ? sorted[(sorted.length - 1) / 2] : (sorted[sorted.length/2 - 1] + sorted[sorted.length/2]) / 2;
    let x, xTicks = [], xMax = 0;
    if (logScale) {
      const lo = Math.log(minM / 1.35), span = Math.log(maxM * 1.3) - lo;
      x = v => L + pw * (Math.log(v) - lo) / span;
      for (let p = 10 ** Math.floor(Math.log10(minM / 1.35)); p <= maxM * 1.3; p *= 10)
        for (const m of [1, 2, 5]) if (m * p >= minM / 1.35 && m * p <= maxM * 1.3) xTicks.push(m * p);
    } else {
      const step = maxM > 200 ? 100 : maxM > 60 ? 50 : 10;
      xMax = Math.ceil(maxM * 1.18 / step) * step;
      x = v => L + pw * v / xMax;
    }
    const y = v => T + ph * (1 - v);
    const xm = x(median), ym = y(.5);
    const share = t => t.neg / t.mentions;
    const radius = t => 7 + 17 * Math.sqrt(t.mentions / maxM);
    const dots = topics.map(t => ({t, r: role(t), cx: x(t.mentions), cy: y(share(t)), rad: radius(t)}));
    const hero = r => ['concern','strength','watch'].includes(r);
    // 라벨: 중요한 주제부터 빈 자리에 놓고, 자리가 없으면 생략(마우스를 올리면 이름이 보임)
    const textW = (str, size) => [...str].reduce((w, ch) => w + (/[ㄱ-힝]/.test(ch) ? size : size * .6), 0);
    const boxes = [], labels = [];
    const hits = (b, edge = W - R) => b.x < L || b.x + b.w > edge || b.y < T || b.y + b.h > H - B + 4
      || boxes.some(o => b.x < o.x + o.w && b.x + b.w > o.x && b.y < o.y + o.h && b.y + b.h > o.y)
      || dots.some(d => { const nx = Math.max(b.x, Math.min(d.cx, b.x + b.w)), ny = Math.max(b.y, Math.min(d.cy, b.y + b.h)); return Math.hypot(d.cx - nx, d.cy - ny) < d.rad + 1; });
    // IPA 네 영역. 오른쪽 = 언급 수 중앙값 이상, 위 = 불만 50% 초과
    const quads = [
      {cls:'is-fix', text:'중점투자 영역', size:14, right:true, top:true},
      {cls:'is-keep', text:'유지강화 영역', size:14, right:true, top:false},
      {cls:'is-watch', text:'점진적 개선 영역', size:13, right:false, top:true},
      {cls:'is-small', text:'현상유지 영역', size:13, right:false, top:false}].map(q => ({...q,
        x0: q.right ? xm : L, x1: q.right ? W - R : xm, y0: q.top ? T : ym, y1: q.top ? ym : H - B,
        n: topics.filter(t => (t.mentions >= median) === q.right && (share(t) > .5) === q.top).length}));
    // 영역 이름 + 주제 수. 자리가 모자라면 주제 수를 빼고 이름만 놓는다.
    const quadLabels = quads.map(q => {
      for (const count of [` ${q.n}개`, '']) {
        const w = textW(q.text, q.size) + textW(count, 13), h = q.size + 4, pad = 8;
        const mid = (q.y0 + q.y1 - h) / 2;
        const corners = q.right
          ? [[q.x1 - pad - w, q.y0 + pad], [q.x1 - pad - w, q.y1 - pad - h], [q.x0 + pad, q.y0 + pad], [q.x0 + pad, q.y1 - pad - h], [q.x1 - pad - w, mid], [q.x0 + pad, mid]]
          : [[q.x0 + pad, q.y0 + pad], [q.x0 + pad, q.y1 - pad - h], [q.x1 - pad - w, q.y0 + pad], [q.x1 - pad - w, q.y1 - pad - h], [q.x0 + pad, mid], [q.x1 - pad - w, mid]];
        const spot = corners.find(([bx, by]) => q.x1 - q.x0 > w + pad * 2 && !hits({x:bx, y:by, w, h}));
        if (!spot) continue;
        boxes.push({x:spot[0], y:spot[1], w, h});
        return `<text class="rd-q-label ${q.cls}" x="${spot[0]}" y="${spot[1] + q.size}" font-size="${q.size}">${q.text}${count ? `<tspan class="rd-q-count">${count}</tspan>` : ''}</text>`;
      }
      return '';
    }).join('');
    const order = [...dots].sort((a,b) => hero(b.r) - hero(a.r) || (b.t.name === selected) - (a.t.name === selected) || b.t.mentions - a.t.mentions);
    order.forEach(d => {
      const big = hero(d.r);
      const size = big ? 14 : 13, sub = big ? `${num(d.t.mentions)}건 · 불만 ${Math.round(share(d.t) * 100)}%` : '';
      const w = Math.max(textW(d.t.name, size), sub ? textW(sub, 13) : 0), h = big ? 33 : 17;
      const g = d.rad + (big ? 9 : 5);
      const k = g * .72;
      const spots = [[d.cx + g, d.cy - h / 2, 'start'], [d.cx - g - w, d.cy - h / 2, 'end'], [d.cx - w / 2, d.cy - g - h, 'middle'], [d.cx - w / 2, d.cy + g, 'middle'],
        [d.cx + k, d.cy - k - h, 'start'], [d.cx - k - w, d.cy - k - h, 'end'], [d.cx + k, d.cy + k, 'start'], [d.cx - k - w, d.cy + k, 'end']];
      for (const [bx, by, anchor] of spots) {
        const b = {x: bx, y: by, w, h};
        // 지킬 것·고칠 것 이름은 반드시 보이도록 카드 여백까지 허용
        if (hits(b, big ? W + 18 : W - R)) continue;
        boxes.push(b);
        const tx = anchor === 'start' ? bx : anchor === 'end' ? bx + w : bx + w / 2;
        labels.push(`<text class="rd-dot-label is-${d.r}" data-action="select" data-theme="${esc(d.t.name)}" x="${tx}" y="${by + size - 1}" text-anchor="${anchor}" font-size="${size}">${esc(d.t.name)}</text>${sub ? `<text class="rd-dot-sub" data-action="select" data-theme="${esc(d.t.name)}" x="${tx}" y="${by + size + 15}" text-anchor="${anchor}">${sub}</text>` : ''}`);
        break;
      }
    });
    const tick = (tx, ty, str, anchor = 'end') => `<text class="rd-map-tick" x="${tx}" y="${ty}" text-anchor="${anchor}">${str}</text>`;
    const axisName = W < 480 ? (logScale ? '언급 수 · 로그 눈금' : `${num(xMax)}건`) : logScale ? '언급 리뷰 수 → · 로그 눈금 · 원 크기도 언급 수' : `언급 리뷰 수 → ${num(xMax)}건 · 원 크기도 언급 수`;
    const xGrid = xTicks.map(v => `<line x1="${x(v)}" x2="${x(v)}" y1="${T}" y2="${H - B}" class="rd-map-grid"/>`).join('');
    const xTickText = xTicks.filter(v => Math.abs(x(v) - xm) > 26).map(v => tick(x(v), H - B + 16, num(v), 'middle')).join('');
    return `<svg class="rd-map" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="group" aria-label="IPA 매트릭스: 언급 수와 불만 비율">
      <defs>
        <linearGradient id="rdQFix" x1="1" y1="0" x2="0" y2="1"><stop offset="0" class="rd-q-stop-fix" stop-opacity=".13"/><stop offset="1" class="rd-q-stop-fix" stop-opacity=".06"/></linearGradient>
        <linearGradient id="rdQKeep" x1="1" y1="1" x2="0" y2="0"><stop offset="0" class="rd-q-stop-keep" stop-opacity=".12"/><stop offset="1" class="rd-q-stop-keep" stop-opacity=".05"/></linearGradient>
      </defs>
      <rect x="${L}" y="${T}" width="${xm - L}" height="${ph}" class="rd-q-rest"/>
      <rect x="${xm}" y="${T}" width="${W - R - xm}" height="${ym - T}" fill="url(#rdQFix)"/>
      <rect x="${xm}" y="${ym}" width="${W - R - xm}" height="${H - B - ym}" fill="url(#rdQKeep)"/>
      ${xGrid}
      <line x1="${L}" x2="${W - R}" y1="${ym}" y2="${ym}" class="rd-map-mid"/>
      <line x1="${xm}" x2="${xm}" y1="${T}" y2="${H - B}" class="rd-map-mid"/>
      <line x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}" class="rd-map-axis"/>
      ${quadLabels}
      ${tick(L - 6, T + 4, '100%')}${tick(L - 6, ym + 4, '50%')}${tick(L - 6, H - B + 4, '0%')}
      ${logScale ? xTickText : tick(L, H - 8, '0', 'start')}${tick(xm, H - 8, `중앙값 ${num(Math.round(median))}건`, 'middle')}${tick(W - R, H - 8, axisName, 'end')}
      ${[...dots].sort((a,b) => (a.t.name === selected || hero(a.r)) - (b.t.name === selected || hero(b.r)) || b.rad - a.rad).map(d => `<g class="rd-dot is-${d.r}" data-action="select" data-theme="${esc(d.t.name)}" tabindex="0" role="button" aria-pressed="${selected === d.t.name}" aria-label="${esc(d.t.name)}: 언급 ${d.t.mentions}건, 불만 ${Math.round(share(d.t) * 100)}%, 칭찬 ${d.t.pos}건, 불만 ${d.t.neg}건"><title>${esc(d.t.name)} · 언급 ${num(d.t.mentions)}건 · 칭찬 ${num(d.t.pos)} · 불만 ${num(d.t.neg)} (${Math.round(share(d.t) * 100)}%)</title>${d.rad < 12 ? `<circle cx="${d.cx}" cy="${d.cy}" r="${d.rad + 6}" class="rd-dot-hit"/>` : ''}${hero(d.r) ? `<circle cx="${d.cx}" cy="${d.cy}" r="${d.rad + 12}" class="rd-dot-halo"/>` : ''}<circle cx="${d.cx}" cy="${d.cy}" r="${d.rad + 6}" class="rd-dot-ring"/><circle cx="${d.cx}" cy="${d.cy}" r="${d.rad}" class="rd-dot-mark"/></g>`).join('')}
      <g aria-hidden="true">${labels.join('')}</g>
    </svg>`;
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
    const when = t.neg && cells.length ? `<section class="rd-sec">
        <h3>이 불만이 나오는 플레이 구간</h3>
        <div class="rd-cols" role="img" aria-label="${cells.map(c => `${c.label} ${c.denominator ? pct(c.rate) : '자료 없음'}`).join(', ')}">
          ${cells.map(c => { const small = c.denominator < 30; const h = small || c.rate == null ? 0 : Math.max(4, c.rate / cellMax * 100);
            const top = !small && c.rate != null && c.rate === cellMax;
            return `<div class="rd-col ${small ? 'is-small' : ''}${top ? ' is-max' : ''}" title="${esc(c.label)} · ${num(c.count)} / ${num(c.denominator)}건${small ? ' · 표본 적음' : ''}"><span class="rd-col-val">${small ? '표본 적음' : pct(c.rate)}</span><span class="rd-col-track"><i style="height:${h}%"></i></span><span class="rd-col-label">${esc(c.label)}</span></div>`; }).join('')}
        </div>
        <p class="rd-note">구간별 AI 분석 리뷰 중 이 주제 불만 비율 · 30건 미만 구간은 표시하지 않음</p>
      </section>` : '';
    target.className = `rd-pane rd-focus is-${r}`;
    target.innerHTML = `
      <header class="rd-pane-head">
        <div><h2>${esc(t.name)}</h2><p><b class="rd-role">${label}</b>${definition ? ` · ${esc(definition)}` : ''}</p></div>
      </header>
      <section class="rd-sec">
        <h3>칭찬과 불만</h3>
        <div class="rd-split" role="img" aria-label="불만 ${t.neg}건, 칭찬 ${t.pos}건">
          <div class="rd-split-labels"><span class="neg">불만 <b>${num(t.neg)}</b> ${Math.round(negShare)}%</span><span class="pos">칭찬 <b>${num(t.pos)}</b> ${Math.round(100 - negShare)}%</span></div>
          <div class="rd-split-bar"><i class="neg" style="width:${negShare}%"></i><i class="pos" style="width:${100 - negShare}%"></i></div>
        </div>
        ${t.neg && t.negative_recommended != null ? `<p class="rd-note">불만을 쓴 ${num(t.neg)}건 중 ${num(t.negative_recommended)}건은 그래도 게임을 추천했습니다${t.negative_recommended / t.neg >= .5 ? '. 떠나게 만들 정도의 불만은 아닐 수 있습니다.' : '. 비추천으로 이어진 불만이 많습니다.'}</p>` : ''}
      </section>
      ${when}
      ${action?.prob ? `<section class="rd-sec"><h3>AI 요약</h3><div class="rd-callout"><p class="rd-body">${esc(action.prob)}</p>${action.why || action.fix?.length ? `<details class="rd-why"><summary>원인과 개선 제안</summary>${action.why ? `<p><b>리뷰가 말하는 원인</b>${esc(action.why)}</p>` : ''}${action.fix?.length ? `<p><b>리뷰에서 나온 제안</b></p><ul>${action.fix.map(f => `<li>${esc(f)}</li>`).join('')}</ul>` : ''}<p class="rd-note">AI가 리뷰를 요약한 내용입니다. 원문으로 확인한 뒤 기획에 반영하세요.</p></details>` : ''}</div></section>` : ''}
      ${quote ? `<section class="rd-sec"><h3>대표 리뷰 <small>${quote.recommended ? '게임 추천' : '게임 비추천'}${quote.hours == null ? '' : ` · ${num(Math.round(quote.hours))}시간 플레이`}</small></h3><blockquote class="rd-quote">${esc(quote.content)}${quote.truncated ? '…' : ''}</blockquote></section>` : ''}
      <footer class="rd-pane-foot rd-focus-actions">
        ${t.neg ? `<button class="rd-btn ${lead === 'N' ? 'primary' : ''}" data-action="evidence" data-sentiment="N">${icon('review')}불만 리뷰 ${num(t.neg)}건</button>` : ''}
        ${t.pos ? `<button class="rd-btn ${lead === 'P' ? 'primary' : ''}" data-action="evidence" data-sentiment="P">${icon('review')}칭찬 리뷰 ${num(t.pos)}건</button>` : ''}
      </footer>`;
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

  // 재미 유형: 가장 많이 언급된 것만 진한 파랑, 나머지는 옅게. 막대 길이 = 긍정·혼합 리뷰 중 비율.
  function renderFun() {
    const target = document.getElementById('rdFunChart');
    const rows = (evidence.fun || []).slice(0, 6);
    if (!rows.length) { target.innerHTML = '<div class="rd-empty">재미 유형이 분류된 리뷰가 없습니다.</div>'; return; }
    const max = Math.max(...rows.map(f => f.share || 0), 1);
    target.innerHTML = `<div class="rd-funs">${rows.map((f, i) => `<div class="rd-fun-row ${i ? '' : 'is-top'}" title="${esc(f.desc)} · ${num(f.count)} / ${num(evidence.fun_denominator)}건">
        <span class="rd-fun-name"><b>${esc(f.name)}</b><small>${esc(f.desc || '')}</small></span>
        <span class="rd-fun-track"><i style="width:${clamp(f.share / max * 100)}%"></i></span>
        <span class="rd-fun-val">${pct(f.share)}</span></div>`).join('')}</div>`;
  }

  function onClick(event) {
    const button = event.target.closest('[data-action]');
    if (!button) return;
    const action = button.dataset.action;
    if (action === 'select') {
      if (!themeByName(button.dataset.theme)) return;
      selected = button.dataset.theme; updateURL(); renderChart(); renderDetail();
      // 좁은 화면에서는 근거 패널이 차트 아래에 있으므로 그쪽으로 이동
      if (innerWidth < 1080) document.getElementById('rdDetail')?.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
    } else if (action === 'expand') { expanded = !expanded; renderTopics(); }
    else if (action === 'view') { view = button.dataset.view; const url = new URL(location.href); url.searchParams.set('view', view); history.replaceState(null, '', url); renderChart(); }
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
  /* ---------- 한 장 보고서: A4 한 쪽. 새 창에서 열고 인쇄(PDF 저장) ---------- */
  function reportHTML() {
    if (!evidence) return '';
    const s = strength(), c = concern() || loudest(), counts = evidence.counts;
    const game = data.game?.name || '게임';
    const period = evidence.period ? `${evidence.period.start.replaceAll('-','.')} – ${evidence.period.end.replaceAll('-','.')}` : '';
    const action = c && data.actions?.find(a => a.theme === c.name);
    const quote = (t, k) => t?.examples?.[k]?.[0]?.content;
    const topicBox = (t, kind) => {
      if (!t) return '';
      const q = quote(t, kind === 'keep' ? 'P' : 'N');
      return `<div class="rpt-topic is-${kind}">
        <span class="rpt-tag">${kind === 'keep' ? '지킬 것' : '고칠 것'}</span><h3>${esc(t.name)}</h3>
        <p class="rpt-num">${kind === 'keep' ? `칭찬 ${Math.round(t.pos / t.mentions * 100)}%` : `불만 ${Math.round(t.neg / t.mentions * 100)}%`} <small>· 언급 ${num(t.mentions)}건 (칭찬 ${num(t.pos)} / 불만 ${num(t.neg)})</small></p>
        ${kind === 'fix' && action?.prob ? `<p><b>문제</b>${esc(action.prob)}</p>` : ''}
        ${kind === 'fix' && action?.why ? `<p><b>원인</b>${esc(action.why)}</p>` : ''}
        ${kind === 'fix' && action?.fix?.length ? `<p><b>유저 제안</b>${action.fix.map(esc).join(' · ')}</p>` : ''}
        ${q ? `<blockquote>“${esc(q.slice(0, 120))}${q.length > 120 ? '…' : ''}”</blockquote>` : ''}</div>`;
    };
    const deep = window.ReviewPages?.deepLines(evidence.deep) || [];
    const design = (data.design_log || []).filter(r => ['무엇을', '얼마나', '주제 합치기', '결론'].includes(r.step));
    return `<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(game)} 리뷰 진단 보고서</title>
<link rel="stylesheet" href="${location.origin}/static/review-dashboard.css">
<style>
@page { size:A4; margin:10mm; }
body { margin:0; background:#F2F4F6; font-family:system-ui,-apple-system,"Segoe UI","Noto Sans KR",sans-serif; }
.rpt { width:186mm; min-height:273mm; margin:16px auto; padding:10mm; box-sizing:border-box; background:#fff; color:#333D4B; font-size:12px; line-height:1.55; }
.rpt-bar { width:186mm; margin:16px auto 0; display:flex; justify-content:flex-end; }
.rpt-bar button { border:0; border-radius:8px; padding:9px 14px; background:#191F28; color:#fff; font:inherit; font-size:13px; cursor:pointer; }
.rpt-kicker { font-size:11px; color:#4E5968; font-weight:600; }
.rpt h1 { margin:4px 0 2px; font-size:22px; letter-spacing:-.03em; color:#191F28; }
.rpt-meta { font-size:11px; color:#5F6977; }
.rpt-summary { margin:8px 0 0; padding:8px 10px; border-radius:8px; background:#F7F9FB; }
.rpt h2 { margin:10px 0 4px; font-size:13px; color:#191F28; }
.rpt .rd-map { width:100%; height:auto; }
.rpt-two { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.rpt-topic { border:1px solid #E5E8EB; border-radius:10px; padding:10px 12px; }
.rpt-topic.is-fix { background:#FFF4F5; border-color:#F8C3C8; } .rpt-topic.is-keep { background:#EEF4FE; border-color:#C8DCF8; }
.rpt-tag { font-size:10px; font-weight:800; color:#fff; background:#1B64DA; border-radius:999px; padding:1px 7px; }
.is-fix .rpt-tag { background:#B42331; }
.rpt-topic h3 { margin:4px 0 0; font-size:16px; color:#191F28; }
.rpt-num { margin:2px 0 6px; font-weight:800; font-size:14px; } .rpt-num small { font-weight:500; font-size:11px; color:#4E5968; }
.rpt-topic p { margin:3px 0; } .rpt-topic p b { color:#191F28; margin-right:6px; }
.rpt blockquote { margin:6px 0 0; padding:6px 8px; border-radius:6px; background:rgba(255,255,255,.7); color:#4E5968; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.rpt-lines { margin:0; padding:0; list-style:none; display:grid; gap:4px; }
.rpt-lines li { display:grid; grid-template-columns:84px 1fr; gap:8px; }
.rpt-lines span { font-weight:700; color:#4E5968; }
.rpt-lines b { color:#B42331; }
.rpt h2 small { font-weight:500; color:#5F6977; font-size:11px; margin-left:4px; }
.rpt-design li { grid-template-columns:110px 1fr; }
.rpt-foot { margin-top:12px; padding-top:8px; border-top:1px solid #E5E8EB; font-size:10px; color:#5F6977; }
@media print { body { background:#fff; } .rpt { margin:0; width:auto; min-height:0; padding:0; font-size:11px; } .rpt-bar { display:none; } .rpt, .rpt-two, .rpt-mini { break-inside:avoid; } }
</style></head><body>
<div class="rpt-bar"><button onclick="print()">인쇄 / PDF로 저장</button></div>
<div class="page active rpt" data-page="overview">
  <div class="rpt-kicker">${esc(game)} · Steam 리뷰 진단 보고서${data.generated_at ? ` · ${esc(data.generated_at)}` : ''}</div>
  <h1>${verdictHTML()}</h1>
  <div class="rpt-meta">${esc(period)} · AI 분석 ${num(counts.analyzed)}건 / 수집 ${num(counts.collected)}건</div>
  ${data.summary ? `<p class="rpt-summary">${esc(data.summary)}</p>` : ''}
  <h2>IPA 매트릭스</h2>${mapSVG(700, 280)}
  <div class="rpt-two">${topicBox(s, 'keep')}${topicBox(c, 'fix')}</div>
  ${deep.length ? `<h2>심층 분석에서 찾은 것</h2><ul class="rpt-lines">${deep.map(([k, t]) => `<li><span>${k}</span><p style="margin:0">${t}</p></li>`).join('')}</ul>` : ''}
  ${design.length ? `<h2>분석 설계 <small>누가 정했나</small></h2><ul class="rpt-lines rpt-design">${design.map(r => `<li><span>${esc(r.step)} · ${esc(r.who)}</span><p style="margin:0">${esc(r.text)}${r.details?.length ? ` — ${r.details.slice(0, 3).map(esc).join(' / ')}` : ''}</p></li>`).join('')}</ul>` : ''}
  <p class="rpt-foot">최신순으로 모은 Steam 리뷰입니다. 전체 유저의 무작위 표본이 아니므로 "전체 유저의 몇 %"로 읽지 않습니다. 주제·감성은 AI 분류이며 한 리뷰가 여러 주제에 들어갈 수 있습니다. 지킬 것·고칠 것은 조사를 시작할 곳이며 개선 효과를 뜻하지 않습니다.</p>
</div></body></html>`;
  }
  function report() {
    const html = reportHTML();
    const w = html && window.open('', '_blank');
    if (!w) return;
    w.document.open(); w.document.write(html); w.document.close();
  }

  return {render, report, reportHTML};
})();
