// TinyWorld — stage life: staggered bubbles, typewriter, shockwave, wander + juice.
(function () {
  var BUBBLE_LIFETIME_MS = 8000;
  var STAGGER_DELAY_MS = 120;

  function animateBubbles() {
    var bubbles = document.querySelectorAll('.bubble:not([data-animated])');
    var i = 0;
    bubbles.forEach(function (b) {
      b.dataset.animated = '1';
      b.dataset.spawned = Date.now();
      b.style.animationDelay = (i * STAGGER_DELAY_MS) + 'ms';
      setTimeout(function () { typewriter(b); }, i * STAGGER_DELAY_MS + 120);
      i++;
    });
    // Juice: trigger roster flash + mood pop for each speaking pawn
    setTimeout(function () {
      document.querySelectorAll('.pawn.speaking').forEach(function (p) {
        var moodEl = p.querySelector('.pawn-mood');
        if (moodEl) { moodEl.classList.remove('pop'); void moodEl.offsetWidth; moodEl.classList.add('pop'); }
      });
      document.querySelectorAll('.roster-card').forEach(function (c) {
        c.classList.remove('speaking-flash'); void c.offsetWidth; c.classList.add('speaking-flash');
      });
    }, 200);
  }

  function typewriter(bubble) {
    var node = bubble.firstChild;
    if (!node || node.nodeType !== 3) return;
    var full = node.textContent;
    if (full.length < 4) return;
    node.textContent = '';
    var k = 0;
    var speed = Math.max(9, Math.min(22, 520 / full.length));
    (function step() {
      if (k < full.length) { node.textContent += full[k++]; setTimeout(step, speed); }
    })();
  }

  function dismissOld() {
    document.querySelectorAll('.bubble[data-spawned]').forEach(function (b) {
      if (Date.now() - parseInt(b.dataset.spawned, 10) > BUBBLE_LIFETIME_MS) {
        b.style.transition = 'opacity .4s ease, transform .4s ease';
        b.style.opacity = '0';
        b.style.transform = 'translateX(-50%) translateY(8px) scale(.9)';
        setTimeout(function () { if (b.parentNode) b.remove(); }, 400);
      }
    });
  }
  setInterval(dismissOld, 1000);

  function fireShockwave() {
    var sw = document.querySelector('.shockwave');
    if (!sw) return;
    sw.classList.remove('fire'); void sw.offsetWidth; sw.classList.add('fire');
    setTimeout(function () { sw.classList.remove('fire'); }, 900);
  }

  // Juice: screen shake on event throw
  function fireScreenShake() {
    var stage = document.querySelector('.stage');
    if (!stage) return;
    stage.classList.remove('shake'); void stage.offsetWidth; stage.classList.add('shake');
    setTimeout(function () { stage.classList.remove('shake'); }, 550);
  }

  // Juice: button pulse on throw
  function fireButtonPulse() {
    var btn = document.querySelector('#throw-btn') || document.querySelector('button.primary');
    if (!btn) return;
    btn.classList.remove('pulse'); void btn.offsetWidth; btn.classList.add('pulse');
    setTimeout(function () { btn.classList.remove('pulse'); }, 2500);
  }

  // Juice: meter tick glow when vibe-fill width changes
  function watchMeters() {
    var fills = document.querySelectorAll('.vibe-fill');
    fills.forEach(function (f) {
      if (f.dataset.watched) return;
      f.dataset.watched = '1';
      var lastW = f.style.width;
      var m = new MutationObserver(function () {
        if (f.style.width !== lastW) {
          lastW = f.style.width;
          f.classList.remove('tick'); void f.offsetWidth; f.classList.add('tick');
        }
      });
      m.observe(f, { attributes: true, attributeFilter: ['style'] });
    });
  }
  setInterval(watchMeters, 500);

  // Juice: day/night tint drift
  function startTintDrift() {
    var tint = document.querySelector('.stage-tint');
    if (tint && !tint.classList.contains('drift')) tint.classList.add('drift');
  }

  // gentle idle wander so the town feels alive between events
  function wander() {
    document.querySelectorAll('.pawn').forEach(function (p) {
      if (p.classList.contains('speaking')) return;
      var dx = (Math.random() * 2 - 1) * 0.7;
      var dy = (Math.random() * 2 - 1) * 0.4;
      var t = p.querySelector('.pawn-token');
      if (t) t.style.transform = 'translate(' + dx.toFixed(2) + 'px,' + dy.toFixed(2) + 'px)';
    });
  }
  setInterval(wander, 2600);

  // Juice: track mouse on buttons for radial highlight
  document.addEventListener('mousemove', function (e) {
    var btn = e.target.closest('button.primary, .gr-button-primary, #throw-btn');
    if (!btn) return;
    var rect = btn.getBoundingClientRect();
    btn.style.setProperty('--mx', ((e.clientX - rect.left) / rect.width * 100) + '%');
    btn.style.setProperty('--my', ((e.clientY - rect.top) / rect.height * 100) + '%');
  });

  var observer = new MutationObserver(function (muts) {
    var fresh = false;
    muts.forEach(function (m) {
      m.addedNodes && m.addedNodes.forEach(function (n) {
        if (n.nodeType === 1 && (n.querySelector ? (n.querySelector('.bubble') || n.classList.contains('bubble')) : false)) fresh = true;
      });
    });
    if (fresh) {
      setTimeout(function () {
        animateBubbles();
        fireShockwave();
        fireScreenShake();
        fireButtonPulse();
        startTintDrift();
      }, 40);
    }
  });

  function watch() {
    var root = document.querySelector('.gradio-container') || document.body;
    if (root) { observer.observe(root, { childList: true, subtree: true }); animateBubbles(); startTintDrift(); }
    else setTimeout(watch, 300);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watch);
  else watch();
})();
