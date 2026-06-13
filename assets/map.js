// TinyWorld — map polish JS
// Shockwave, screen-shake, staggered bubbles, typewriter, bubble auto-dismiss

(function () {
  const BUBBLE_LIFETIME_MS = 8000;
  const STAGGER_DELAY_MS = 80;

  /* ── Shockwave ring on trigger ── */
  function triggerShockwave() {
    var mapEl = document.querySelector('.tw-map');
    if (!mapEl) return;

    // Create two concentric rings for depth
    for (var i = 0; i < 2; i++) {
      var ring = document.createElement('div');
      ring.className = 'shockwave-ring';
      if (i === 1) ring.style.animationDelay = '0.15s';
      mapEl.appendChild(ring);
      (function (el) {
        setTimeout(function () { el.remove(); }, 1200);
      })(ring);
    }

    // Screen-shake
    document.body.classList.add('screen-shake');
    setTimeout(function () {
      document.body.classList.remove('screen-shake');
    }, 180);
  }

  /* ── Staggered bubble spring-in + typewriter ── */
  function animateBubbles() {
    var bubbles = document.querySelectorAll('.speech-bubble');
    var index = 0;
    bubbles.forEach(function (b) {
      if (b.dataset.animated) return;
      b.dataset.animated = '1';

      // Stagger: hide initially, reveal with delay
      b.style.opacity = '0';
      b.style.transform = 'translateX(-50%) scale(0)';
      var delay = index * STAGGER_DELAY_MS;
      index++;

      setTimeout(function () {
        b.style.transition = 'opacity 0.3s ease, transform 0.35s cubic-bezier(.2,.8,.2,1)';
        b.style.opacity = '1';
        b.style.transform = 'translateX(-50%) scale(1)';

        // Typewriter: wrap text content, reveal char by char
        typewriterReveal(b);
      }, delay);
    });
  }

  function typewriterReveal(bubble) {
    var textNode = bubble.firstChild;
    if (!textNode || textNode.nodeType !== 3) return;

    var fullText = textNode.textContent;
    if (fullText.length < 3) return;

    textNode.textContent = '';
    var charIndex = 0;
    var speed = Math.max(12, Math.min(30, 600 / fullText.length));

    function typeNext() {
      if (charIndex < fullText.length) {
        textNode.textContent += fullText[charIndex];
        charIndex++;
        setTimeout(typeNext, speed);
      }
    }
    typeNext();
  }

  /* ── Bubble auto-dismiss ── */
  function dismissOldBubbles() {
    var bubbles = document.querySelectorAll('.speech-bubble');
    bubbles.forEach(function (b) {
      if (!b.dataset.spawned) {
        b.dataset.spawned = Date.now();
      }
      var age = Date.now() - parseInt(b.dataset.spawned, 10);
      if (age > BUBBLE_LIFETIME_MS) {
        b.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        b.style.opacity = '0';
        b.style.transform = 'translateX(-50%) scale(0.8)';
        setTimeout(function () { b.remove(); }, 500);
      }
    });
  }

  setInterval(dismissOldBubbles, 1000);

  /* ── Observer: detect new bubbles → animate + shockwave ── */
  var isFirstRender = true;

  var observer = new MutationObserver(function (mutations) {
    var hasNewBubbles = false;
    for (var m = 0; m < mutations.length; m++) {
      var nodes = mutations[m].addedNodes;
      for (var n = 0; n < nodes.length; n++) {
        var node = nodes[n];
        if (node.nodeType === 1) {
          if (node.classList && node.classList.contains('speech-bubble')) {
            hasNewBubbles = true;
          }
          if (node.querySelector && node.querySelector('.speech-bubble')) {
            hasNewBubbles = true;
          }
        }
      }
    }

    if (hasNewBubbles) {
      if (!isFirstRender) {
        triggerShockwave();
      }
      isFirstRender = false;
      setTimeout(animateBubbles, 50);

      // Hide idle overlay when bubbles appear
      var idle = document.querySelector('.idle-overlay');
      if (idle) idle.classList.remove('visible');
    }
  });

  /* ── Active-speaker glow ── */
  function highlightSpeaker(name) {
    // Remove previous glow
    var prev = document.querySelector('.tile.speaking');
    if (prev) prev.classList.remove('speaking');

    // Find character tile by matching emoji text
    var tiles = document.querySelectorAll('.tile');
    tiles.forEach(function (tile) {
      var nameEl = tile.querySelector('.char-emoji');
      if (nameEl && nameEl.textContent.trim()) {
        // Match by position in roster order
        var moodEl = tile.querySelector('.char-mood');
        if (moodEl && moodEl.title) {
          // Use the mood title as a proxy — we'll match by grid position instead
        }
      }
    });
  }

  // Watch for audio element changes (auto-play voice)
  var audioObserver = new MutationObserver(function (mutations) {
    for (var m = 0; m < mutations.length; m++) {
      var target = mutations[m].target;
      if (target.tagName === 'AUDIO' && target.src) {
        // Voice is playing — could highlight speaker here
        break;
      }
    }
  });

  function watchAudio() {
    var audioEls = document.querySelectorAll('audio');
    audioEls.forEach(function (a) {
      audioObserver.observe(a, { attributes: true, attributeFilter: ['src'] });
    });
  }

  setTimeout(watchAudio, 1000);

  function watchMap() {
    var mapEl = document.querySelector('.tw-map');
    if (mapEl) {
      observer.observe(mapEl, { childList: true, subtree: true });
    } else {
      setTimeout(watchMap, 500);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', watchMap);
  } else {
    watchMap();
  }
})();
