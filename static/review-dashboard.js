/* 리뷰 진단 화면. 한 문장 결론 → 주제별 칭찬·불만 차트 → 선택 주제 근거 → 플레이 시간.
   모든 막대와 문장은 현재 게임의 evidence 집계로만 그린다. 설계 규칙은 AGENTS.md 참고. */
window.ReviewDashboard = (() => {
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = x => x == null ? '—' : Number(x).toLocaleString('ko-KR');
  const pct = x => x == null ? '—' : `${Number(x).toFixed(1)}%`;
  const clamp = x => Math.max(0, Math.min(100, Number(x) || 0));
  const COLLAPSED_ROWS = 10, MAX_CONCERN_ROWS = 4;
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
  // 도넛 링: 빨강(불만)을 12시부터 시계 방향, 나머지를 파랑(칭찬)으로. 2px 틈으로 두 색을 가른다.
  function ringArcs(cx, cy, r, sw, negShare) {
    const c = 2 * Math.PI * r, neg = c * negShare, gap = negShare > 0 && negShare < 1 ? Math.min(2, c * .02) : 0;
    const arc = (len, rot, cls) => len > 0 ? `<circle cx="${cx}" cy="${cy}" r="${r}" class="${cls}" stroke-width="${sw}" fill="none" stroke-dasharray="${Math.max(0, len - gap)} ${c}" transform="rotate(${rot} ${cx} ${cy})"/>` : '';
    return arc(neg, -90, 'rd-arc-neg') + arc(c - neg, -90 + negShare * 360, 'rd-arc-pos');
  }
  function ringSVG(size, negShare, center, sub) {
    const r = size / 2 - 7, cx = size / 2;
    return `<svg class="rd-ring" viewBox="0 0 ${size} ${size}" width="${size}" height="${size}" aria-hidden="true"><circle cx="${cx}" cy="${cx}" r="${r}" fill="none" class="rd-arc-track" stroke-width="10"/>${ringArcs(cx, cx, r, 10, negShare)}<text x="${cx}" y="${cx + (sub ? 2 : 6)}" text-anchor="middle" class="rd-ring-num">${center}</text>${sub ? `<text x="${cx}" y="${cx + 17}" text-anchor="middle" class="rd-ring-sub">${sub}</text>` : ''}</svg>`;
  }
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
    const inline = !['cards','panel'].includes(new URLSearchParams(location.search).get('proto'));
    const mini = (t, kind) => inline ? `<span class="rd-hl-ring" title="${kind === 'pos' ? `칭찬 ${Math.round(t.pos / t.mentions * 100)}%` : `불만 ${Math.round(t.neg / t.mentions * 100)}%`}">${ringSVG(40, t.neg / t.mentions, `${Math.round((kind === 'pos' ? t.pos : t.neg) / t.mentions * 100)}`)}</span>` : '';
    const pos = t => `${mini(t, 'pos')}<span class="rd-hl rd-hl-pos">${esc(t.name)}</span>${topicJosa(t.name)}`;
    const neg = t => `${mini(t, 'neg')}<span class="rd-hl rd-hl-neg">${esc(t.name)}</span>${topicJosa(t.name)}`;
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
    view = params.get('view') === 'bars' ? 'bars' : 'map';
    root.innerHTML = `
      <div class="rd-hero">
        <section class="rd-chart-card" aria-labelledby="rdTopicsTitle">
          <div class="rd-chart-head">
            <h2 id="rdTopicsTitle"></h2>
            <p id="rdTopicsNote"></p>
            <div class="rd-toggle rd-view-toggle" aria-label="차트 보기"><button data-action="view" data-view="map">우선순위 지도</button><button data-action="view" data-view="bars">칭찬·불만 막대</button></div>
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
        <p><b>우선순위 지도</b><br>가로축은 주제를 언급한 AI 분석 리뷰 수(칭찬+불만), 세로축은 그중 불만 비율입니다. 원 크기도 언급 수입니다. 세로 점선은 전체 주제의 언급 수 중앙값, 가로 점선은 불만 50%입니다. 오른쪽 위 칸은 많이 언급되면서 불만이 더 많은 주제입니다.</p>
        <p><b>칭찬·불만 막대</b><br>막대 길이는 해당 주제를 칭찬하거나 불만으로 언급한 AI 분석 리뷰 수입니다. 양쪽이 같은 눈금을 씁니다. 칭찬이 더 많은 주제는 위에서 칭찬순, 불만이 더 많은 주제는 아래 구역에서 불만순으로 놓입니다.</p>
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
    root.onkeydown = event => {
      if ((event.key === 'Enter' || event.key === ' ') && event.target.matches?.('.rd-dot')) { event.preventDefault(); event.target.dispatchEvent(new MouseEvent('click', {bubbles:true})); }
    };
    if (!resizeBound) {
      resizeBound = true;
      let timer;
      addEventListener('resize', () => { clearTimeout(timer); timer = setTimeout(() => { if (view === 'map' && document.getElementById('rdTopicChart')) renderChart(); }, 150); });
    }
    renderAnchors(); renderChart(); renderDetail(); renderCohorts();
  }

  // 시안 비교용: 기본은 결론 문장 안 작은 링(③). ?proto=cards 는 머리말 링 카드(①), ?proto=panel 은 패널 링만(②).
  // 머리말 오른쪽: 지킬 것·고칠 것 링 카드. 누르면 해당 주제를 고른다.
  function renderAnchors() {
    const box = document.getElementById('rdAnchors');
    if (!box) return;
    const proto = new URLSearchParams(location.search).get('proto');
    const card = (t, kind) => {
      if (!t) return '';
      const neg = t.neg / t.mentions, main = kind === 'keep' ? 1 - neg : neg;
      return `<button class="rd-anchor is-${kind}" type="button" data-theme="${esc(t.name)}" onclick="ReviewDashboard.select(this.dataset.theme)">${ringSVG(64, neg, `${Math.round(main * 100)}%`)}<span><em>${kind === 'keep' ? '지킬 것' : '고칠 것'}</em><b>${esc(t.name)}</b><small>언급 ${num(t.mentions)}건 중 ${kind === 'keep' ? `칭찬 ${num(t.pos)}` : `불만 ${num(t.neg)}`}건</small></span></button>`;
    };
    box.innerHTML = proto !== 'cards' ? '' : card(strength(), 'keep') + card(concern() || loudest(), 'fix');
  }

  function renderChart() {
    const title = {map:'주제 우선순위 지도', bars:'주제별 칭찬과 불만'}[view];
    const note = {map:'', bars:'리뷰 수 · 주제를 누르면 근거가 나옵니다'}[view];
    document.getElementById('rdTopicsTitle').textContent = title;
    document.getElementById('rdTopicsNote').textContent = note;
    root.querySelectorAll('[data-action="view"]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.view === view)));
    if (view === 'map') renderMap(); else renderTopics();
  }

  // 우선순위 지도: x = 언급 수, y = 불만 비율, 원 크기 = 언급 수. 점선은 언급 수 중앙값과 불만 50%.
  function renderMap() {
    const target = document.getElementById('rdTopicChart');
    const topics = evidence.themes.filter(t => t.mentions > 0);
    if (!topics.length) { target.innerHTML = '<div class="rd-empty">분류된 주제가 아직 없습니다.</div>'; return; }
    const W = Math.max(300, target.clientWidth || 800), H = W < 480 ? 320 : Math.round(Math.min(520, Math.max(380, W * .5)));
    const L = 40, R = 12, T = 16, B = 30, pw = W - L - R, ph = H - T - B;
    const maxM = Math.max(...topics.map(t => t.mentions));
    const step = maxM > 200 ? 100 : maxM > 60 ? 50 : 10;
    const xMax = Math.ceil(maxM * 1.18 / step) * step;
    const sorted = topics.map(t => t.mentions).sort((a,b) => a - b);
    const median = sorted.length % 2 ? sorted[(sorted.length - 1) / 2] : (sorted[sorted.length/2 - 1] + sorted[sorted.length/2]) / 2;
    const x = v => L + pw * v / xMax, y = v => T + ph * (1 - v);
    const xm = x(median), ym = y(.5);
    const share = t => t.neg / t.mentions;
    const radius = t => 5 + 19 * Math.sqrt(t.mentions / maxM);
    const fills = {concern:'var(--rd-neg)', watch:'var(--rd-neg)', disliked:'var(--rd-neg-mid)', strength:'var(--rd-pos)', praised:'var(--rd-pos-mute)'};
    const dots = topics.map(t => ({t, r: role(t), cx: x(t.mentions), cy: y(share(t)), rad: radius(t)}));
    // 라벨: 중요한 주제부터 빈 자리에 놓고, 자리가 없으면 생략(마우스를 올리면 이름이 보임)
    const textW = (str, size) => [...str].reduce((w, ch) => w + (/[\u3131-\uD79D]/.test(ch) ? size : size * .6), 0);
    const boxes = [], labels = [];
    const hits = (b, edge = W - R) => b.x < L || b.x + b.w > edge || b.y < T || b.y + b.h > H - B + 4
      || boxes.some(o => b.x < o.x + o.w && b.x + b.w > o.x && b.y < o.y + o.h && b.y + b.h > o.y)
      || dots.some(d => { const nx = Math.max(b.x, Math.min(d.cx, b.x + b.w)), ny = Math.max(b.y, Math.min(d.cy, b.y + b.h)); return Math.hypot(d.cx - nx, d.cy - ny) < d.rad + 1; });
    const quads = [
      {cls:'is-fix', text:'먼저 고칠 것', size:14, x0:xm, x1:W - R, y0:T, y1:ym},
      {cls:'is-keep', text:'지킬 강점', size:14, x0:xm, x1:W - R, y0:ym, y1:H - B},
      {cls:'is-watch', text:'지켜볼 불만', size:13, x0:L, x1:xm, y0:T, y1:ym},
      {cls:'is-small', text:'작은 강점', size:13, x0:L, x1:xm, y0:ym, y1:H - B}];
    const quadLabels = quads.map(q => {
      const w = textW(q.text, q.size), h = q.size + 4, pad = 8;
      const corners = q.cls === 'is-fix' || q.cls === 'is-keep'
        ? [[q.x1 - pad - w, q.y0 + pad], [q.x1 - pad - w, q.y1 - pad - h], [q.x0 + pad, q.y0 + pad], [q.x0 + pad, q.y1 - pad - h]]
        : [[q.x0 + pad, q.y0 + pad], [q.x0 + pad, q.y1 - pad - h], [q.x1 - pad - w, q.y0 + pad], [q.x1 - pad - w, q.y1 - pad - h]];
      const spot = corners.find(([bx, by]) => q.x1 - q.x0 > w + pad * 2 && !hits({x:bx, y:by, w, h})) ;
      if (!spot) return '';
      boxes.push({x:spot[0], y:spot[1], w, h});
      return `<text class="rd-q-label ${q.cls}" x="${spot[0]}" y="${spot[1] + q.size}">${q.text}</text>`;
    }).join('');
    const order = [...dots].sort((a,b) => (b.r === 'concern' || b.r === 'strength' || b.r === 'watch') - (a.r === 'concern' || a.r === 'strength' || a.r === 'watch')
      || (b.t.name === selected) - (a.t.name === selected) || b.t.mentions - a.t.mentions);
    order.forEach(d => {
      const hero = ['concern','strength','watch'].includes(d.r);
      const size = hero ? 14 : 13, sub = hero ? `${num(d.t.mentions)}건 · 불만 ${Math.round(share(d.t) * 100)}%` : '';
      const w = Math.max(textW(d.t.name, size), sub ? textW(sub, 12) : 0), h = hero ? 32 : 17;
      const g = d.rad + 5;
      const k = g * .72;
      const spots = [[d.cx + g, d.cy - h / 2, 'start'], [d.cx - g - w, d.cy - h / 2, 'end'], [d.cx - w / 2, d.cy - g - h, 'middle'], [d.cx - w / 2, d.cy + g, 'middle'],
        [d.cx + k, d.cy - k - h, 'start'], [d.cx - k - w, d.cy - k - h, 'end'], [d.cx + k, d.cy + k, 'start'], [d.cx - k - w, d.cy + k, 'end']];
      for (const [bx, by, anchor] of spots) {
        const b = {x: bx, y: by, w, h};
        // 지킬 것·고칠 것 이름은 반드시 보이도록 카드 여백까지 허용
        if (hits(b, hero ? W + 18 : W - R)) continue;
        boxes.push(b);
        const tx = anchor === 'start' ? bx : anchor === 'end' ? bx + w : bx + w / 2;
        labels.push(`<text class="rd-dot-label is-${d.r}" data-action="select" data-theme="${esc(d.t.name)}" x="${tx}" y="${by + size - 1}" text-anchor="${anchor}" font-size="${size}">${esc(d.t.name)}</text>${sub ? `<text class="rd-dot-sub" data-action="select" data-theme="${esc(d.t.name)}" x="${tx}" y="${by + size + 14}" text-anchor="${anchor}">${sub}</text>` : ''}`);
        break;
      }
    });
    const tick = (tx, ty, str, anchor = 'end') => `<text class="rd-map-tick" x="${tx}" y="${ty}" text-anchor="${anchor}">${str}</text>`;
    target.innerHTML = `<svg class="rd-map" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="group" aria-label="주제 우선순위 지도">
      <rect x="${xm}" y="${T}" width="${W - R - xm}" height="${ym - T}" class="rd-q rd-q-fix"/>
      <rect x="${xm}" y="${ym}" width="${W - R - xm}" height="${H - B - ym}" class="rd-q rd-q-keep"/>
      <rect x="${L}" y="${T}" width="${xm - L}" height="${ym - T}" class="rd-q rd-q-watch"/>
      <line x1="${L}" x2="${W - R}" y1="${ym}" y2="${ym}" class="rd-map-mid"/>
      <line x1="${xm}" x2="${xm}" y1="${T}" y2="${H - B}" class="rd-map-mid"/>
      <line x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}" class="rd-map-axis"/>
      ${quadLabels}
      ${tick(L - 6, T + 4, '100%')}${tick(L - 6, ym + 4, '50%')}${tick(L - 6, H - B + 4, '0%')}
      ${tick(L, H - 8, '0', 'start')}${tick(xm, H - 8, `중앙값 ${num(Math.round(median))}건`, 'middle')}${tick(W - R, H - 8, W < 480 ? `${num(xMax)}건` : `언급 리뷰 수 → ${num(xMax)}건 · 원 크기도 언급 수`, 'end')}
      ${[...dots].sort((a,b) => (a.t.name === selected || ['concern','strength','watch'].includes(a.r)) - (b.t.name === selected || ['concern','strength','watch'].includes(b.r)) || b.rad - a.rad).map(d => `<g class="rd-dot is-${d.r}" data-action="select" data-theme="${esc(d.t.name)}" tabindex="0" role="button" aria-pressed="${selected === d.t.name}" aria-label="${esc(d.t.name)}: 언급 ${d.t.mentions}건, 불만 ${Math.round(share(d.t) * 100)}%, 칭찬 ${d.t.pos}건, 불만 ${d.t.neg}건"><title>${esc(d.t.name)} · 언급 ${num(d.t.mentions)}건 · 칭찬 ${num(d.t.pos)} · 불만 ${num(d.t.neg)} (${Math.round(share(d.t) * 100)}%)</title>${d.rad < 12 ? `<circle cx="${d.cx}" cy="${d.cy}" r="${d.rad + 6}" class="rd-dot-hit"/>` : ''}<circle cx="${d.cx}" cy="${d.cy}" r="${d.rad}" class="rd-dot-mark"/>${ringArcs(d.cx, d.cy, d.rad - Math.max(3.5, d.rad * .42) / 2, Math.max(3.5, d.rad * .42), share(d.t))}</g>`).join('')}
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
      ${new URLSearchParams(location.search).get('proto') !== 'cards' ? `<div class="rd-focus-ring" role="img" aria-label="불만 ${t.neg}건, 칭찬 ${t.pos}건">${ringSVG(112, negShare / 100, `${Math.round(t.neg > t.pos ? negShare : 100 - negShare)}%`, t.neg > t.pos ? '불만' : '칭찬')}<div><span class="neg"><b>${num(t.neg)}</b> 불만</span><span class="pos"><b>${num(t.pos)}</b> 칭찬</span></div></div>` : `<div class="rd-split" role="img" aria-label="불만 ${t.neg}건, 칭찬 ${t.pos}건">
        <div class="rd-split-labels"><span class="neg"><b>${num(t.neg)}</b> 불만 ${Math.round(negShare)}%</span><span class="pos">칭찬 ${Math.round(100 - negShare)}% <b>${num(t.pos)}</b></span></div>
        <div class="rd-split-bar"><i class="neg" style="width:${negShare}%"></i><i class="pos" style="width:${100 - negShare}%"></i></div>
      </div>`}
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
  function select(name) { if (!themeByName(name)) return; selected = name; updateURL(); renderChart(); renderDetail(); }
  return {render, select};
})();
