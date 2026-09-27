// 게임기획 스튜디오 공통 계약: 마우스 사이드 버튼(4번 뒤로·5번 앞으로)과 스튜디오 상단 뒤로가기.
// 이 도구는 페이지 이동(홈 → 대시보드)이라 브라우저 방문 기록으로 오간다.
// 도구 안에 갈 곳이 없으면 스튜디오에 넘긴다.
(function () {
  var CHANNEL = 'game-design-studio:tool-navigation';
  var hosted = window.parent !== window;
  var nav = window.navigation;

  function can(direction) {
    if (nav && typeof nav.canGoBack === 'boolean') return direction === 'back' ? nav.canGoBack : nav.canGoForward;
    // iframe의 history.length는 스튜디오 전체 기록과 섞여 믿을 수 없다. 모르면 스튜디오에 넘긴다.
    return false;
  }

  function step(direction) {
    if (!can(direction)) return false;
    if (direction === 'back') history.back(); else history.forward();
    return true;
  }

  function swallow(event) { if (event.button === 3 || event.button === 4) event.preventDefault(); }
  window.addEventListener('mousedown', swallow);
  window.addEventListener('auxclick', swallow);
  window.addEventListener('mouseup', function (event) {
    if (event.button !== 3 && event.button !== 4) return;
    event.preventDefault();
    var direction = event.button === 3 ? 'back' : 'forward';
    if (!step(direction) && hosted) {
      window.parent.postMessage({ channel: CHANNEL, type: 'side-navigate', direction: direction }, '*');
    }
  });
  window.addEventListener('message', function (event) {
    if (event.source !== window.parent || !event.data || event.data.channel !== CHANNEL || event.data.type !== 'navigate-back') return;
    var handled = step('back');
    window.parent.postMessage({ channel: CHANNEL, type: 'navigate-back:result', requestId: event.data.requestId, handled: handled }, '*');
  });
})();
