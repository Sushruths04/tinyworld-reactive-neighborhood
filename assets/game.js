// TinyWorld — canvas isometric town: futuristic buildings, park, fountain,
// steering-physics characters that spread to in-character destinations.
// Data in via hidden textareas: #tw-world (board+cast, hot-swappable for map
// switching) and #tw-reactions (per-throw, polled).
(function () {
  function $(s) { return document.querySelector(s); }
  function txt(s) { var e = $(s + ' textarea') || $(s + ' input'); return e ? e.value : ''; }

  function micBanner() {
    if (document.getElementById('tw-mic-warn')) return;
    if (location.hostname === '0.0.0.0' || (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1')) {
      var b = document.createElement('div'); b.id = 'tw-mic-warn'; b.className = 'tw-mic-warn';
      var port = location.port ? ':' + location.port : '';
      b.innerHTML = '⚠ For the microphone, open <b>http://localhost' + port + '</b> — voice input is blocked on this address (' + location.hostname + '). Typing works everywhere.';
      document.body.appendChild(b);
    }
  }

  function boot() {
    var canvas = document.getElementById('tw-canvas');
    if (!canvas) return setTimeout(boot, 200);
    micBanner();
    if (window.__TW) return;
    window.__TW = engine(canvas);
    window.__TW.start();
  }

  function engine(canvas) {
    var ctx = canvas.getContext('2d');
    var DPR = Math.min(window.devicePixelRatio || 1, 2);
    var TS = 64, TH = 32;
    var S = { W: null, raw: '', chars: [], tiles: {}, scale: 1, ox: 0, oy: 0, waves: [], lastTs: 0 };

    function shade(hex, f) {
      var n = parseInt(hex.slice(1), 16), r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
      r = Math.min(255, r * f); g = Math.min(255, g * f); b = Math.min(255, b * f);
      return 'rgb(' + (r | 0) + ',' + (g | 0) + ',' + (b | 0) + ')';
    }
    function iso(gx, gy) { return { x: S.ox + (gx - gy) * (TS / 2) * S.scale, y: S.oy + (gx + gy) * (TH / 2) * S.scale }; }

    function loadWorld(W) {
      S.W = W; S.tiles = {};
      (W.roads.cols || []).forEach(function (c) { for (var r = 0; r < W.rows; r++) S.tiles[c + ',' + r] = 'road'; });
      (W.roads.rows || []).forEach(function (r) { for (var c = 0; c < W.cols; c++) S.tiles[c + ',' + r] = 'road'; });
      (W.plaza || []).forEach(function (p) { S.tiles[p[0] + ',' + p[1]] = 'plaza'; });
      S.chars = W.cast.map(function (c) {
        return {
          name: c.name, short: c.short, emoji: c.emoji, color: c.color,
          x: c.home[0], y: c.home[1], vx: 0, vy: 0, tx: c.home[0], ty: c.home[1], home: c.home.slice(),
          moodEmoji: '', bubble: null, bubbleAt: 0, speaking: false, activity: '', vehicle: '', running: false,
          idle: 1 + Math.random() * 4, bob: Math.random() * 6, returnAt: 0
        };
      });
      S.spots = (W.hotspots ? Object.keys(W.hotspots).map(function (k) { return W.hotspots[k]; }) : []);
      // ---- physics: tiles nobody can walk into (buildings, water, tree trunks) ----
      S.blocked = {};
      function block(gx, gy) { S.blocked[Math.round(gx) + ',' + Math.round(gy)] = 1; }
      W.buildings.forEach(function (b) { for (var bx = b.gx; bx < b.gx + b.w; bx++) for (var by = b.gy; by < b.gy + b.d; by++) block(bx, by); });
      (W.props || []).forEach(function (p) {
        if (p.type === 'pond') { for (var px = 0; px < (p.w || 2); px++) for (var py = 0; py < (p.d || 2); py++) block(p.gx + px, p.gy + py); }
        else if (p.type === 'fountain') { block(p.gx, p.gy); block(p.gx - 0.5, p.gy - 0.5); block(p.gx + 0.5, p.gy + 0.5); }
      });
      (W.trees || []).forEach(function (t) { block(t[0], t[1]); });
      // never trap a character: a home/spawn tile stays walkable even if it overlaps scenery
      S.chars.forEach(function (c) { delete S.blocked[Math.round(c.home[0]) + ',' + Math.round(c.home[1])]; });
      // seats people can amble over to and rest at, so the town isn't a permanent jog
      S.seats = [];
      (W.props || []).forEach(function (p) { if (p.type === 'bench' || p.type === 'patio' || p.type === 'table') S.seats.push([Math.round(p.gx), Math.round(p.gy) + 1]); });
      // ambient crowd — pedestrians, a cyclist, dogs that bring the town to life
      var SHIRTS = ['#c85a54', '#4a7bc8', '#caa23f', '#5aa86a', '#8a6fc0', '#c86fa0', '#3f9c9c', '#b5703f'];
      var HAIR = ['#2a2018', '#4a3526', '#6b6b6b', '#161616', '#5a3a22', '#3a2a40', '#7a6a55'];
      var n = (W.ambient != null) ? W.ambient : 6;
      S.amb = [];
      for (var i = 0; i < n; i++) {
        var t = randWalkable();
        var type = (i % 6 === 0) ? 'dog' : ((i % 6 === 1) ? 'bike' : 'ped');
        S.amb.push({
          type: type, x: t[0], y: t[1], vx: 0, vy: 0, tx: t[0], ty: t[1],
          sp: (type === 'bike' ? 1.0 : 0.5) + Math.random() * 0.4,
          idle: Math.random() * 3, ph: Math.random() * 6, face: 1,
          shirt: SHIRTS[i % SHIRTS.length], hair: HAIR[i % HAIR.length],
          sc: (type === 'dog' ? 0.85 : 1.1),
          follow: type === 'dog' ? Math.floor(Math.random() * S.chars.length) : -1
        });
      }
      // cars are off unless a world opts in (W.traffic), and they cruise slowly when on
      var CARC = ['#d24b4b', '#3f6fb0', '#d6b13f', '#4a9c6a', '#8a8f9c'], ci = 0;
      S.cars = [];
      if (W.traffic) {
        (W.roads.rows || []).forEach(function (r) { S.cars.push({ axis: 'h', line: r, pos: Math.random() * W.cols, dir: Math.random() < 0.5 ? 1 : -1, sp: 0.5 + Math.random() * 0.3, color: CARC[ci++ % CARC.length] }); });
        (W.roads.cols || []).forEach(function (c) { S.cars.push({ axis: 'v', line: c, pos: Math.random() * W.rows, dir: Math.random() < 0.5 ? 1 : -1, sp: 0.5 + Math.random() * 0.3, color: CARC[ci++ % CARC.length] }); });
      }
      S.waves = [];
      fit();
    }

    function randWalkable() {
      for (var k = 0; k < 30; k++) { var gx = Math.floor(Math.random() * S.W.cols), gy = Math.floor(Math.random() * S.W.rows); if (walkable(gx, gy)) return [gx, gy]; }
      return [S.W.cols >> 1, S.W.rows >> 1];
    }

    function fit() {
      if (!S.W) return;
      var rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(1, rect.width * DPR); canvas.height = Math.max(1, rect.height * DPR);
      var minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
      for (var gy = 0; gy <= S.W.rows; gy++) for (var gx = 0; gx <= S.W.cols; gx++) {
        var x = (gx - gy) * TS / 2, y = (gx + gy) * TH / 2;
        if (x < minX) minX = x; if (x > maxX) maxX = x; if (y < minY) minY = y; if (y > maxY) maxY = y;
      }
      var bw = maxX - minX, bh = (maxY - minY) + 130;
      S.scale = Math.min(rect.width / bw, rect.height / bh) * 1.06;
      S.ox = rect.width / 2 - ((minX + maxX) / 2) * S.scale;
      S.oy = rect.height / 2 - ((minY + maxY) / 2) * S.scale + 18 * S.scale;
    }
    window.addEventListener('resize', fit);

    function walkable(gx, gy) {
      gx = Math.round(gx); gy = Math.round(gy);
      if (gx < 0 || gy < 0 || gx >= S.W.cols || gy >= S.W.rows) return false;
      return !(S.blocked && S.blocked[gx + ',' + gy]);
    }

    // ---------- tiles ----------
    function drawTile(gx, gy) {
      var t = S.tiles[gx + ',' + gy] || 'grass';
      var a = iso(gx, gy), b = iso(gx + 1, gy), c = iso(gx + 1, gy + 1), d = iso(gx, gy + 1);
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.lineTo(c.x, c.y); ctx.lineTo(d.x, d.y); ctx.closePath();
      var fill = ((gx + gy) % 2 === 0) ? '#1e6b3e' : '#1a6038';
      if (t === 'road') fill = ((gx + gy) % 2 === 0) ? '#33384c' : '#2e3344';
      else if (t === 'plaza') fill = '#46415f';
      ctx.fillStyle = fill; ctx.fill();
      ctx.strokeStyle = 'rgba(120,200,255,0.07)'; ctx.lineWidth = 1; ctx.stroke();
      if (t === 'road') {
        ctx.strokeStyle = 'rgba(255,215,106,0.45)'; ctx.lineWidth = Math.max(1, 1.6 * S.scale);
        ctx.setLineDash([5 * S.scale, 5 * S.scale]); ctx.beginPath();
        ctx.moveTo((a.x + d.x) / 2, (a.y + d.y) / 2); ctx.lineTo((b.x + c.x) / 2, (b.y + c.y) / 2);
        ctx.stroke(); ctx.setLineDash([]);
      }
    }

    // ---------- buildings ----------
    function corners(b, H) {
      var bt = iso(b.gx, b.gy), br = iso(b.gx + b.w, b.gy), bb = iso(b.gx + b.w, b.gy + b.d), bl = iso(b.gx, b.gy + b.d);
      return { bt: bt, br: br, bb: bb, bl: bl, tt: u(bt, H), tr: u(br, H), tb: u(bb, H), tl: u(bl, H) };
      function u(p, h) { return { x: p.x, y: p.y - h }; }
    }
    function quad(p0, p1, p2, p3, fill) { ctx.fillStyle = fill; ctx.beginPath(); ctx.moveTo(p0.x, p0.y); ctx.lineTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.lineTo(p3.x, p3.y); ctx.closePath(); ctx.fill(); }
    // p0=base-near, p1=base-far, p2=top-far, p3=top-near
    function onQuad(p0, p1, p2, p3, u, v) {
      var ax = p0.x + (p1.x - p0.x) * u, ay = p0.y + (p1.y - p0.y) * u;
      var bx = p3.x + (p2.x - p3.x) * u, by = p3.y + (p2.y - p3.y) * u;
      return { x: ax + (bx - ax) * v, y: ay + (by - ay) * v };
    }
    function windowGrid(p0, p1, p2, p3, cols, rows, f) {
      var ws = 3.4 * S.scale;
      for (var i = 1; i <= cols; i++) for (var j = 1; j <= rows; j++) {
        var q = onQuad(p0, p1, p2, p3, i / (cols + 1), j / (rows + 1));
        var lit = ((i * 7 + j * 3) % 4 !== 0);
        ctx.fillStyle = 'rgba(10,14,26,0.85)'; ctx.fillRect(q.x - ws, q.y - ws, ws * 2, ws * 2);
        ctx.fillStyle = lit ? 'rgba(255,232,150,' + (0.78 * f) + ')' : 'rgba(120,160,210,' + (0.4 * f) + ')';
        ctx.fillRect(q.x - ws * 0.7, q.y - ws * 0.7, ws * 1.4, ws * 1.4);
      }
    }
    function door(p0, p1, p2, p3, col) {
      var b = onQuad(p0, p1, p2, p3, 0.5, 0.02), t = onQuad(p0, p1, p2, p3, 0.5, 0.22);
      var w = 4 * S.scale;
      ctx.fillStyle = shade(col, 0.5);
      ctx.beginPath(); ctx.moveTo(b.x - w, b.y); ctx.lineTo(b.x + w, b.y); ctx.lineTo(t.x + w, t.y); ctx.lineTo(t.x - w, t.y); ctx.closePath(); ctx.fill();
    }

    function drawBuilding(b, now) {
      var H = b.h * S.scale, kind = b.kind || 'block';
      var c = corners(b, H);
      // ground shadow
      quad(c.bt, c.br, { x: c.bb.x + 7, y: c.bb.y + 7 }, c.bl, 'rgba(0,0,0,0.30)');
      // walls
      quad(c.bl, c.bb, c.tb, c.tl, shade(b.wall, 0.7));   // left
      quad(c.br, c.bb, c.tb, c.tr, shade(b.wall, 1.0));   // right
      var floors = Math.max(2, Math.round(b.h / 16));
      windowGrid(c.bl, c.bb, c.tb, c.tl, Math.max(2, b.d), floors, 0.7);
      windowGrid(c.br, c.bb, c.tb, c.tr, Math.max(2, b.w), floors, 1.0);
      // subtle edge highlight
      ctx.strokeStyle = shade(b.roof, 1.0); ctx.lineWidth = 1.2 * S.scale;
      ctx.beginPath(); ctx.moveTo(c.bb.x, c.bb.y); ctx.lineTo(c.tb.x, c.tb.y); ctx.stroke();
      // roof / crown
      ctx.save(); ctx.shadowColor = b.roof; ctx.shadowBlur = 7 * S.scale;
      if (kind === 'dome') {
        var cx = (c.tt.x + c.tb.x) / 2, cy = (c.tt.y + c.tb.y) / 2;
        var rw = Math.abs(c.tr.x - c.tl.x) / 2, rh = Math.abs(c.tb.y - c.tt.y) / 2 + 14 * S.scale;
        quad(c.tt, c.tr, c.tb, c.tl, shade(b.roof, 0.85));
        var g = ctx.createLinearGradient(cx, cy - rh, cx, cy); g.addColorStop(0, shade(b.roof, 1.3)); g.addColorStop(1, b.roof);
        ctx.fillStyle = g; ctx.beginPath(); ctx.ellipse(cx, cy, rw, rh, 0, Math.PI, 2 * Math.PI); ctx.fill();
      } else if (kind === 'tower') {
        quad(c.tt, c.tr, c.tb, c.tl, b.roof);
        // antenna + pulsing beacon
        var apex = { x: (c.tt.x + c.tb.x) / 2, y: (c.tt.y + c.tb.y) / 2 };
        ctx.strokeStyle = shade(b.roof, 1.2); ctx.lineWidth = 1.6 * S.scale;
        ctx.beginPath(); ctx.moveTo(apex.x, apex.y); ctx.lineTo(apex.x, apex.y - 22 * S.scale); ctx.stroke();
        var pulse = 0.5 + 0.5 * Math.sin(now / 350);
        ctx.fillStyle = 'rgba(56,232,255,' + pulse + ')';
        ctx.beginPath(); ctx.arc(apex.x, apex.y - 22 * S.scale, 3.2 * S.scale, 0, 7); ctx.fill();
      } else if (kind === 'house') { // residential — pitched gable roof, no neon
        ctx.shadowBlur = 0;
        var rh = 13 * S.scale;
        function upR(p) { return { x: p.x, y: p.y - rh }; }
        var rA = upR({ x: (c.tt.x + c.tl.x) / 2, y: (c.tt.y + c.tl.y) / 2 });
        var rB = upR({ x: (c.tr.x + c.tb.x) / 2, y: (c.tr.y + c.tb.y) / 2 });
        quad(c.tt, c.tr, rB, rA, shade(b.roof, 1.05));   // sunlit slope
        quad(c.tl, c.tb, rB, rA, shade(b.roof, 0.74));   // shaded slope
        tri(c.tt, c.tl, rA, shade(b.wall, 1.08));        // gable end
        tri(c.tr, c.tb, rB, shade(b.wall, 0.92));        // gable end
        ctx.strokeStyle = shade(b.roof, 1.2); ctx.lineWidth = 1.4 * S.scale;
        ctx.beginPath(); ctx.moveTo(rA.x, rA.y); ctx.lineTo(rB.x, rB.y); ctx.stroke(); // ridge
      } else { // block — setback crown
        quad(c.tt, c.tr, c.tb, c.tl, b.roof);
        var inH = 16 * S.scale;
        var sb = { gx: b.gx + b.w * 0.25, gy: b.gy + b.d * 0.25, w: b.w * 0.5, d: b.d * 0.5 };
        var cc = corners(sb, H + inH);
        // shift base of crown up to roof level
        var lift = H;
        function L(p) { return { x: p.x, y: p.y }; }
        var cb = corners(sb, 0);
        var ct = corners(sb, inH);
        function up(p) { return { x: p.x, y: p.y - lift }; }
        quad(up(cb.bl), up(cb.bb), up(ct.tb), up(ct.tl), shade(b.wall, 0.8));
        quad(up(cb.br), up(cb.bb), up(ct.tb), up(ct.tr), shade(b.wall, 1.05));
        quad(up(ct.tt), up(ct.tr), up(ct.tb), up(ct.tl), shade(b.roof, 1.1));
      }
      ctx.restore();
      // ground-floor storefront only for shops/civic buildings — houses just get a door
      if (kind === 'house') { door(c.br, c.bb, c.tb, c.tr, b.wall); houseSign(b, c); }
      else drawStorefront(b, c);
    }
    function tri(a, b, d, fill) { ctx.fillStyle = fill; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.lineTo(d.x, d.y); ctx.closePath(); ctx.fill(); }
    // small house number / family plate above the door (not a glowing holo sign)
    function houseSign(b, c) {
      if (!b.label) return;
      var p = onQuad(c.br, c.bb, c.tb, c.tr, 0.5, 0.34);
      ctx.font = '600 ' + (7 * S.scale) + 'px Rajdhani, sans-serif';
      var tw = ctx.measureText(b.label).width + 8 * S.scale;
      ctx.fillStyle = 'rgba(18,14,10,0.8)'; rr(p.x - tw / 2, p.y - 6 * S.scale, tw, 11 * S.scale, 2 * S.scale); ctx.fill();
      ctx.fillStyle = '#e8dcc0'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(b.label, p.x, p.y);
    }

    // street-level retail on the most-visible (right) wall: p0=br p1=bb p2=tb p3=tr
    function drawStorefront(b, c) {
      var p0 = c.br, p1 = c.bb, p2 = c.tb, p3 = c.tr, accent = b.roof;
      // big glowing shop windows along the ground floor
      var cols = Math.max(2, Math.round(b.w * 1.6));
      for (var i = 1; i <= cols; i++) {
        var wt = onQuad(p0, p1, p2, p3, i / (cols + 1), 0.175), wb = onQuad(p0, p1, p2, p3, i / (cols + 1), 0.03);
        var ww = 5 * S.scale, wh = wb.y - wt.y;
        ctx.fillStyle = 'rgba(6,10,20,0.92)'; ctx.fillRect(wt.x - ww, wt.y, ww * 2, wh);
        ctx.fillStyle = 'rgba(255,222,158,0.92)'; ctx.fillRect(wt.x - ww * 0.78, wt.y + 1.2 * S.scale, ww * 1.56, wh - 2.4 * S.scale);
        ctx.fillStyle = 'rgba(255,255,255,0.18)'; ctx.fillRect(wt.x - ww * 0.78, wt.y + 1.2 * S.scale, ww * 0.5, wh - 2.4 * S.scale);
      }
      door(p0, p1, p2, p3, b.wall);
      // awning: a coloured strip that juts toward the street with a scalloped valance
      var al = onQuad(p0, p1, p2, p3, 0.05, 0.205), ar = onQuad(p0, p1, p2, p3, 0.95, 0.205), jut = 9 * S.scale, seg = 8;
      function lerp(t) { return { x: al.x + (ar.x - al.x) * t, y: al.y + (ar.y - al.y) * t }; }
      for (var k = 0; k < seg; k++) {
        var a0 = lerp(k / seg), a1 = lerp((k + 1) / seg);
        ctx.fillStyle = (k % 2) ? shade(accent, 1.25) : shade(accent, 0.92);
        ctx.beginPath(); ctx.moveTo(a0.x, a0.y); ctx.lineTo(a1.x, a1.y); ctx.lineTo(a1.x, a1.y + jut); ctx.lineTo(a0.x, a0.y + jut); ctx.closePath(); ctx.fill();
        ctx.fillStyle = shade(accent, 0.78);
        ctx.beginPath(); ctx.moveTo(a0.x, a0.y + jut); ctx.lineTo(a1.x, a1.y + jut); ctx.lineTo((a0.x + a1.x) / 2, (a0.y + a1.y) / 2 + jut + 4 * S.scale); ctx.closePath(); ctx.fill();
      }
      // shop sign mounted on the façade above the awning (replaces the old floating word)
      if (b.label) {
        var sc = onQuad(p0, p1, p2, p3, 0.5, 0.40);
        ctx.font = '700 ' + (8.5 * S.scale) + 'px Orbitron, sans-serif';
        var tw = ctx.measureText(b.label).width + 12 * S.scale, th = 14 * S.scale;
        ctx.fillStyle = 'rgba(6,10,20,0.94)'; rr(sc.x - tw / 2, sc.y - th / 2, tw, th, 3 * S.scale); ctx.fill();
        ctx.strokeStyle = shade(accent, 1.2); ctx.lineWidth = 1.3 * S.scale; ctx.stroke();
        ctx.save(); ctx.shadowColor = accent; ctx.shadowBlur = 6 * S.scale;
        ctx.fillStyle = shade(accent, 1.3); ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(b.label, sc.x, sc.y);
        ctx.restore();
      }
    }

    // ---------- props ----------
    function drawProp(p, now) {
      if (p.type === 'fountain') {
        var c = iso(p.gx, p.gy);
        ctx.fillStyle = 'rgba(40,60,90,0.9)'; ctx.beginPath(); ctx.ellipse(c.x, c.y, 22 * S.scale, 11 * S.scale, 0, 0, 7); ctx.fill();
        ctx.fillStyle = '#2bc7ff'; ctx.beginPath(); ctx.ellipse(c.x, c.y, 18 * S.scale, 8 * S.scale, 0, 0, 7); ctx.fill();
        for (var k = 0; k < 3; k++) {
          var t = (now / 700 + k / 3) % 1, rr2 = 4 + t * 14;
          ctx.strokeStyle = 'rgba(160,235,255,' + (0.6 * (1 - t)) + ')'; ctx.lineWidth = 1.4 * S.scale;
          ctx.beginPath(); ctx.ellipse(c.x, c.y, rr2 * S.scale, rr2 * 0.5 * S.scale, 0, 0, 7); ctx.stroke();
        }
        ctx.strokeStyle = 'rgba(180,240,255,0.8)'; ctx.lineWidth = 2 * S.scale;
        ctx.beginPath(); ctx.moveTo(c.x, c.y - 4 * S.scale); ctx.lineTo(c.x, c.y - 16 * S.scale); ctx.stroke();
      } else if (p.type === 'pond') {
        var a = iso(p.gx, p.gy), b = iso(p.gx + (p.w || 2), p.gy), d = iso(p.gx + (p.w || 2), p.gy + (p.d || 2)), e = iso(p.gx, p.gy + (p.d || 2));
        var g = ctx.createLinearGradient(a.x, a.y, d.x, d.y); g.addColorStop(0, '#1f6fa8'); g.addColorStop(1, '#0e4a78');
        ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.lineTo(d.x, d.y); ctx.lineTo(e.x, e.y); ctx.closePath(); ctx.fill();
        ctx.strokeStyle = 'rgba(160,220,255,0.4)'; ctx.lineWidth = 1; ctx.stroke();
      } else if (p.type === 'bench') {
        var c2 = iso(p.gx + 0.5, p.gy + 0.5);
        ctx.fillStyle = '#6a4a2e'; ctx.fillRect(c2.x - 8 * S.scale, c2.y - 4 * S.scale, 16 * S.scale, 4 * S.scale);
      } else if (p.type === 'lamp') {
        var c3 = iso(p.gx + 0.5, p.gy + 0.5);
        ctx.strokeStyle = '#556'; ctx.lineWidth = 2 * S.scale; ctx.beginPath(); ctx.moveTo(c3.x, c3.y); ctx.lineTo(c3.x, c3.y - 22 * S.scale); ctx.stroke();
        var rg = ctx.createRadialGradient(c3.x, c3.y - 22 * S.scale, 1, c3.x, c3.y - 22 * S.scale, 12 * S.scale);
        rg.addColorStop(0, 'rgba(255,235,150,0.9)'); rg.addColorStop(1, 'rgba(255,235,150,0)');
        ctx.fillStyle = rg; ctx.beginPath(); ctx.arc(c3.x, c3.y - 22 * S.scale, 12 * S.scale, 0, 7); ctx.fill();
      } else if (p.type === 'patio') {
        var c4 = iso(p.gx + 0.5, p.gy + 0.5);
        ctx.fillStyle = '#d65b5b'; ctx.beginPath(); ctx.moveTo(c4.x, c4.y - 16 * S.scale); ctx.lineTo(c4.x - 11 * S.scale, c4.y - 7 * S.scale); ctx.lineTo(c4.x + 11 * S.scale, c4.y - 7 * S.scale); ctx.closePath(); ctx.fill();
        ctx.strokeStyle = '#888'; ctx.lineWidth = 1.5 * S.scale; ctx.beginPath(); ctx.moveTo(c4.x, c4.y - 7 * S.scale); ctx.lineTo(c4.x, c4.y); ctx.stroke();
      } else if (p.type === 'table') {       // café table with chairs + parasol
        var ct = iso(p.gx + 0.5, p.gy + 0.5), s = S.scale;
        [[-9, 1], [9, 1], [0, -5], [0, 6]].forEach(function (o) {
          ctx.fillStyle = '#39425a'; ctx.beginPath(); ctx.ellipse(ct.x + o[0] * s, ct.y + o[1] * s * 0.6, 2.8 * s, 1.6 * s, 0, 0, 7); ctx.fill();
          ctx.fillStyle = '#2a3146'; ctx.fillRect(ct.x + o[0] * s - 2.4 * s, ct.y + o[1] * s * 0.6 - 5 * s, 4.8 * s, 5 * s);
        });
        ctx.fillStyle = 'rgba(0,0,0,0.25)'; ctx.beginPath(); ctx.ellipse(ct.x, ct.y + 2 * s, 8 * s, 3.5 * s, 0, 0, 7); ctx.fill();
        ctx.strokeStyle = '#7a8398'; ctx.lineWidth = 1.6 * s; ctx.beginPath(); ctx.moveTo(ct.x, ct.y - 1 * s); ctx.lineTo(ct.x, ct.y + 3 * s); ctx.stroke();
        ctx.fillStyle = '#cdd6ea'; ctx.beginPath(); ctx.ellipse(ct.x, ct.y - 3 * s, 7 * s, 3.2 * s, 0, 0, 7); ctx.fill();
        ctx.strokeStyle = '#8a93a8'; ctx.lineWidth = 1.4 * s; ctx.beginPath(); ctx.moveTo(ct.x, ct.y - 4 * s); ctx.lineTo(ct.x, ct.y - 17 * s); ctx.stroke();
        ctx.fillStyle = '#d65b5b'; ctx.beginPath(); ctx.moveTo(ct.x, ct.y - 22 * s); ctx.lineTo(ct.x - 11 * s, ct.y - 15 * s); ctx.lineTo(ct.x + 11 * s, ct.y - 15 * s); ctx.closePath(); ctx.fill();
        ctx.fillStyle = '#b94a4a'; for (var pz = 0; pz < 3; pz += 2) { ctx.beginPath(); ctx.moveTo(ct.x - 11 * s + pz * 7.3 * s, ct.y - 15 * s); ctx.lineTo(ct.x - 3.7 * s + pz * 7.3 * s, ct.y - 15 * s); ctx.lineTo(ct.x - 7.3 * s + pz * 7.3 * s, ct.y - 18.5 * s); ctx.closePath(); ctx.fill(); }
      } else if (p.type === 'stall') {       // market stall: counter, goods, striped canopy
        var cs = iso(p.gx + 0.5, p.gy + 0.5), s2 = S.scale, col = p.color || '#caa23f';
        ctx.fillStyle = 'rgba(0,0,0,0.25)'; ctx.beginPath(); ctx.ellipse(cs.x, cs.y + 2 * s2, 15 * s2, 4 * s2, 0, 0, 7); ctx.fill();
        ctx.fillStyle = '#5a4632'; ctx.fillRect(cs.x - 13 * s2, cs.y - 6 * s2, 26 * s2, 8 * s2);
        ctx.fillStyle = '#48372a'; ctx.fillRect(cs.x - 13 * s2, cs.y - 6 * s2, 26 * s2, 2 * s2);
        ['#e5663e', '#e0b53f', '#5aa86a', '#d6543f'].forEach(function (gc, gi) { ctx.fillStyle = gc; ctx.beginPath(); ctx.arc(cs.x - 9 * s2 + gi * 6 * s2, cs.y - 7 * s2, 2.6 * s2, 0, 7); ctx.fill(); });
        ctx.strokeStyle = '#6a5a48'; ctx.lineWidth = 1.8 * s2; ctx.beginPath();
        ctx.moveTo(cs.x - 13 * s2, cs.y - 6 * s2); ctx.lineTo(cs.x - 13 * s2, cs.y - 22 * s2);
        ctx.moveTo(cs.x + 13 * s2, cs.y - 6 * s2); ctx.lineTo(cs.x + 13 * s2, cs.y - 22 * s2); ctx.stroke();
        for (var q = 0; q < 7; q++) { ctx.fillStyle = (q % 2) ? col : shade(col, 1.28); ctx.fillRect(cs.x - 13 * s2 + q * (26 / 7) * s2, cs.y - 25 * s2, (26 / 7) * s2 + 0.5, 5 * s2); }
        ctx.fillStyle = shade(col, 0.85); for (var v = 0; v < 7; v++) { var vx = cs.x - 13 * s2 + (v + 0.5) * (26 / 7) * s2; ctx.beginPath(); ctx.moveTo(vx - (13 / 7) * s2, cs.y - 20 * s2); ctx.lineTo(vx + (13 / 7) * s2, cs.y - 20 * s2); ctx.lineTo(vx, cs.y - 17 * s2); ctx.closePath(); ctx.fill(); }
      } else if (p.type === 'planter') {     // raised flower bed
        var cp = iso(p.gx + 0.5, p.gy + 0.5), s3 = S.scale;
        ctx.fillStyle = '#5a4632'; ctx.fillRect(cp.x - 8 * s3, cp.y - 3 * s3, 16 * s3, 5 * s3);
        ctx.fillStyle = '#48372a'; ctx.fillRect(cp.x - 8 * s3, cp.y - 3 * s3, 16 * s3, 1.6 * s3);
        var fc = ['#f06ea0', '#ffd76a', '#7CFFB2', '#d65b5b'];
        for (var f = 0; f < 5; f++) { ctx.fillStyle = '#2f8f55'; ctx.fillRect(cp.x - 6 * s3 + f * 3 * s3, cp.y - 7 * s3, 1.4 * s3, 4 * s3); ctx.fillStyle = fc[f % fc.length]; ctx.beginPath(); ctx.arc(cp.x - 5.3 * s3 + f * 3 * s3, cp.y - 8 * s3, 1.8 * s3, 0, 7); ctx.fill(); }
      }
    }

    function drawTree(t) {
      var p = iso(t[0] + 0.5, t[1] + 0.5);
      ctx.fillStyle = 'rgba(0,0,0,0.22)'; ctx.beginPath(); ctx.ellipse(p.x, p.y, 10 * S.scale, 5 * S.scale, 0, 0, 7); ctx.fill();
      ctx.fillStyle = '#4a2e1a'; ctx.fillRect(p.x - 2 * S.scale, p.y - 13 * S.scale, 4 * S.scale, 13 * S.scale);
      var g = ctx.createRadialGradient(p.x - 4 * S.scale, p.y - 22 * S.scale, 2, p.x, p.y - 18 * S.scale, 15 * S.scale);
      g.addColorStop(0, '#5fe0a0'); g.addColorStop(1, '#1c7a4a'); ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(p.x, p.y - 18 * S.scale, 12 * S.scale, 0, 7); ctx.fill();
    }

    // ---------- sprite primitives ----------
    // a little walking person; returns head-top y for bubble/mood anchoring
    function person(x, y, sc, shirt, hair, ph, moving) {
      var s = S.scale * sc;
      ctx.fillStyle = 'rgba(0,0,0,0.28)'; ctx.beginPath(); ctx.ellipse(x, y, 7 * s, 2.8 * s, 0, 0, 7); ctx.fill();
      var sw = moving ? Math.sin(ph) * 3 * s : 0.6 * s;
      var lift = moving ? Math.abs(Math.cos(ph)) * 1.1 * s : 0;
      ctx.lineCap = 'round';
      // legs
      ctx.strokeStyle = '#34384e'; ctx.lineWidth = 2.6 * s;
      ctx.beginPath(); ctx.moveTo(x, y - 8 * s); ctx.lineTo(x - 2.4 * s + sw, y); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(x, y - 8 * s); ctx.lineTo(x + 2.4 * s - sw, y); ctx.stroke();
      var ty = y - 8 * s - lift;
      // arms (behind torso)
      ctx.strokeStyle = shade(shirt, 0.82); ctx.lineWidth = 2.3 * s;
      ctx.beginPath(); ctx.moveTo(x - 3.5 * s, ty - 8 * s); ctx.lineTo(x - 6 * s - sw * 0.5, ty - 1.5 * s); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(x + 3.5 * s, ty - 8 * s); ctx.lineTo(x + 6 * s + sw * 0.5, ty - 1.5 * s); ctx.stroke();
      // torso
      ctx.fillStyle = shirt; rr(x - 4.6 * s, ty - 12 * s, 9.2 * s, 13 * s, 3 * s); ctx.fill();
      // head
      var hcy = ty - 16 * s;
      ctx.fillStyle = '#e7b893'; ctx.beginPath(); ctx.arc(x, hcy, 4.6 * s, 0, 7); ctx.fill();
      ctx.fillStyle = hair; ctx.beginPath(); ctx.arc(x, hcy - 1.4 * s, 4.7 * s, Math.PI, 2 * Math.PI); ctx.fill();
      return hcy - 5 * s;
    }
    function dog(x, y, sc, ph, moving) {
      var s = S.scale * sc, wag = moving ? Math.sin(ph * 1.4) * 2 * s : 0;
      ctx.fillStyle = 'rgba(0,0,0,0.26)'; ctx.beginPath(); ctx.ellipse(x, y, 8 * s, 3 * s, 0, 0, 7); ctx.fill();
      ctx.fillStyle = '#8a6a45'; rr(x - 7 * s, y - 8 * s, 12 * s, 6 * s, 3 * s); ctx.fill(); // body
      ctx.strokeStyle = '#6a4f33'; ctx.lineWidth = 1.8 * s; // legs
      ctx.beginPath(); ctx.moveTo(x - 5 * s, y - 3 * s); ctx.lineTo(x - 5 * s, y); ctx.moveTo(x + 3 * s, y - 3 * s); ctx.lineTo(x + 3 * s, y); ctx.stroke();
      ctx.fillStyle = '#8a6a45'; ctx.beginPath(); ctx.arc(x + 6 * s, y - 9 * s, 3.4 * s, 0, 7); ctx.fill(); // head
      ctx.strokeStyle = '#8a6a45'; ctx.lineWidth = 2 * s; ctx.beginPath(); ctx.moveTo(x - 7 * s, y - 7 * s); ctx.lineTo(x - 10 * s - wag, y - 9 * s); ctx.stroke(); // tail
    }
    function wheel(x, y, r, ph) {
      ctx.strokeStyle = '#1a1d28'; ctx.lineWidth = 2.2 * S.scale; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.stroke();
      ctx.strokeStyle = 'rgba(200,210,230,0.5)'; ctx.lineWidth = 1 * S.scale;
      for (var a = 0; a < 3; a++) { var an = ph + a * 2.1; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.cos(an) * r, y + Math.sin(an) * r); ctx.stroke(); }
    }
    function bike(x, y, ph, moving, shirt) {
      var s = S.scale;
      ctx.fillStyle = 'rgba(0,0,0,0.28)'; ctx.beginPath(); ctx.ellipse(x, y, 12 * s, 3 * s, 0, 0, 7); ctx.fill();
      var spin = moving ? ph * 2 : 0;
      wheel(x - 7 * s, y - 4 * s, 4.6 * s, spin); wheel(x + 7 * s, y - 4 * s, 4.6 * s, spin);
      ctx.strokeStyle = '#cfd6ea'; ctx.lineWidth = 1.8 * s; // frame
      ctx.beginPath(); ctx.moveTo(x - 7 * s, y - 4 * s); ctx.lineTo(x, y - 4 * s); ctx.lineTo(x + 7 * s, y - 4 * s); ctx.moveTo(x, y - 4 * s); ctx.lineTo(x + 2 * s, y - 12 * s); ctx.stroke();
      // rider
      var rsw = moving ? Math.sin(ph) * 2 * s : 0;
      ctx.fillStyle = shirt; rr(x - 2.5 * s, y - 19 * s, 7 * s, 9 * s, 2.5 * s); ctx.fill();
      ctx.fillStyle = '#e7b893'; ctx.beginPath(); ctx.arc(x + 1 * s, y - 21 * s, 3.6 * s, 0, 7); ctx.fill();
      ctx.strokeStyle = shade(shirt, 0.8); ctx.lineWidth = 1.8 * s;
      ctx.beginPath(); ctx.moveTo(x + 1 * s, y - 15 * s); ctx.lineTo(x + 7 * s, y - 8 * s); ctx.stroke(); // arm to bars
      ctx.beginPath(); ctx.moveTo(x + 1 * s, y - 11 * s); ctx.lineTo(x - 1 * s + rsw, y - 4 * s); ctx.stroke(); // leg pedaling
      return y - 26 * s;
    }

    // ---------- ambient crowd ----------
    function stepAmbient(a, dt) {
      if (a.follow >= 0 && S.chars[a.follow]) { var f = S.chars[a.follow]; a.tx = f.x + 0.7; a.ty = f.y + 0.7; }
      var dx = a.tx - a.x, dy = a.ty - a.y, d = Math.hypot(dx, dy);
      if (d > 0.05) {
        var sp = a.sp * Math.min(1, d / 1.0);
        a.vx += ((dx / d) * sp - a.vx) * Math.min(1, dt * 4);
        a.vy += ((dy / d) * sp - a.vy) * Math.min(1, dt * 4);
        var nx = a.x + a.vx * dt, ny = a.y + a.vy * dt;
        if (walkable(nx, a.y)) a.x = nx; else { a.vx = 0; a.tx = a.x; }
        if (walkable(a.x, ny)) a.y = ny; else { a.vy = 0; a.ty = a.y; }
        a.ph += dt * 6;
      } else if (a.follow < 0) {
        a.idle -= dt;
        if (a.idle <= 0) { var t = randWalkable(); a.tx = t[0]; a.ty = t[1]; a.idle = 2.5 + Math.random() * 5; }
      }
    }
    function drawAmbient(a) {
      var p = iso(a.x + 0.5, a.y + 0.5), mv = Math.hypot(a.vx, a.vy) > 0.08;
      if (a.type === 'dog') dog(p.x, p.y, a.sc, a.ph, mv);
      else if (a.type === 'bike') bike(p.x, p.y, a.ph, mv, a.shirt);
      else person(p.x, p.y, a.sc, a.shirt, a.hair, a.ph, mv);
    }
    function stepCar(c, dt) {
      var max = (c.axis === 'h') ? S.W.cols : S.W.rows; c.pos += c.dir * c.sp * dt;
      if (c.pos < 0) { c.pos = 0; c.dir = 1; } if (c.pos > max) { c.pos = max; c.dir = -1; }
    }
    function drawCar(c) {
      var gx = (c.axis === 'h') ? c.pos : c.line + 0.5, gy = (c.axis === 'h') ? c.line + 0.5 : c.pos, p = iso(gx, gy);
      var s = S.scale, fwd = c.dir > 0 ? 1 : -1;
      ctx.fillStyle = 'rgba(0,0,0,0.32)'; ctx.beginPath(); ctx.ellipse(p.x, p.y, 13 * s, 4.5 * s, 0, 0, 7); ctx.fill();
      // wheels
      ctx.fillStyle = '#15171f'; ctx.beginPath(); ctx.arc(p.x - 7 * s, p.y - 2 * s, 2.6 * s, 0, 7); ctx.arc(p.x + 7 * s, p.y - 2 * s, 2.6 * s, 0, 7); ctx.fill();
      // body
      var g = ctx.createLinearGradient(p.x, p.y - 13 * s, p.x, p.y - 2 * s); g.addColorStop(0, shade(c.color, 1.15)); g.addColorStop(1, c.color);
      ctx.fillStyle = g; rr(p.x - 11 * s, p.y - 9 * s, 22 * s, 8 * s, 3 * s); ctx.fill();
      // cabin
      ctx.fillStyle = shade(c.color, 1.05); rr(p.x - 5 * s, p.y - 14 * s, 11 * s, 6 * s, 2.5 * s); ctx.fill();
      ctx.fillStyle = 'rgba(180,225,255,0.9)'; rr(p.x - 3.5 * s, p.y - 13 * s, 8 * s, 4 * s, 1.5 * s); ctx.fill();
      // lights
      ctx.fillStyle = 'rgba(255,240,180,0.95)'; ctx.beginPath(); ctx.arc(p.x + 10 * s * fwd, p.y - 6 * s, 1.6 * s, 0, 7); ctx.fill();
      ctx.fillStyle = 'rgba(255,90,90,0.9)'; ctx.beginPath(); ctx.arc(p.x - 10 * s * fwd, p.y - 6 * s, 1.4 * s, 0, 7); ctx.fill();
    }

    // ---------- characters ----------
    function drawChar(c, now) {
      var p = iso(c.x + 0.5, c.y + 0.5);
      var moving = Math.hypot(c.vx, c.vy) > 0.08;
      if (c.speaking) {
        var pr = 1 + Math.sin(now / 220) * 0.12;
        ctx.strokeStyle = 'rgba(56,232,255,0.9)'; ctx.lineWidth = 2.4 * S.scale;
        ctx.beginPath(); ctx.ellipse(p.x, p.y, 13 * S.scale * pr, 5.5 * S.scale * pr, 0, 0, 7); ctx.stroke();
      }
      var hy = (c.vehicle === 'bike') ? bike(p.x, p.y, c.bob, moving, c.color)
                                      : person(p.x, p.y, 1.35, c.color, '#241c14', c.bob, moving);
      if (c.moodEmoji) { ctx.font = (12 * S.scale) + 'px serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(c.moodEmoji, p.x + 9 * S.scale, hy + 3 * S.scale); }
      var label = c.short + (c.activity ? '  ' + c.activity : '');
      ctx.font = '600 ' + (9.5 * S.scale) + 'px Rajdhani, sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      var nw = ctx.measureText(label).width + 12 * S.scale;
      ctx.fillStyle = 'rgba(8,12,24,0.8)'; rr(p.x - nw / 2, p.y + 3 * S.scale, nw, 13 * S.scale, 5 * S.scale); ctx.fill();
      ctx.strokeStyle = c.color; ctx.lineWidth = 1; ctx.stroke();
      ctx.fillStyle = '#eaf0ff'; ctx.fillText(label, p.x, p.y + 9.5 * S.scale);
      if (c.bubble) drawBubble(c, p.x, hy, now);
    }
    function drawBubble(c, x, topY, now) {
      var shown = Math.min(c.bubble.length, Math.floor((now - c.bubbleAt) / 22));
      var s = c.bubble.slice(0, shown) || ' ';
      ctx.font = '600 ' + (12 * S.scale) + 'px Rajdhani, sans-serif';
      var maxW = 180 * S.scale, lines = wrap(s, maxW), lh = 15 * S.scale, pad = 8 * S.scale;
      var bw = 0; lines.forEach(function (l) { bw = Math.max(bw, ctx.measureText(l).width); });
      bw += pad * 2; var bh = lines.length * lh + pad * 2;
      var bx = x - bw / 2, by = topY - 14 * S.scale - bh;
      ctx.fillStyle = 'rgba(12,18,34,0.93)'; rr(bx, by, bw, bh, 8 * S.scale); ctx.fill();
      ctx.strokeStyle = 'rgba(120,200,255,0.4)'; ctx.lineWidth = 1; ctx.stroke();
      ctx.fillStyle = 'rgba(12,18,34,0.93)'; ctx.beginPath(); ctx.moveTo(x - 6 * S.scale, by + bh); ctx.lineTo(x + 6 * S.scale, by + bh); ctx.lineTo(x, by + bh + 8 * S.scale); ctx.closePath(); ctx.fill();
      ctx.fillStyle = '#eaf0ff'; ctx.textAlign = 'left'; ctx.textBaseline = 'top';
      lines.forEach(function (l, i) { ctx.fillText(l, bx + pad, by + pad + i * lh); });
      ctx.textAlign = 'center';
    }
    function wrap(s, maxW) {
      var w = s.split(' '), out = [], cur = '';
      for (var i = 0; i < w.length; i++) { var t = cur ? cur + ' ' + w[i] : w[i]; if (ctx.measureText(t).width > maxW && cur) { out.push(cur); cur = w[i]; } else cur = t; }
      if (cur) out.push(cur); return out.slice(0, 4);
    }
    function rr(x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }

    // ---------- physics ----------
    function step(c, dt, now) {
      var dx = c.tx - c.x, dy = c.ty - c.y, dist = Math.hypot(dx, dy);
      if (dist > 0.04) {
        var maxV = (c.vehicle === 'bike') ? 1.9 : (c.running ? 1.3 : 0.85), arrive = 1.1;
        var sp = maxV * Math.min(1, dist / arrive);
        c.vx += ((dx / dist) * sp - c.vx) * Math.min(1, dt * 5);
        c.vy += ((dy / dist) * sp - c.vy) * Math.min(1, dt * 5);
        // resolve per-axis so people slide along walls and never walk into buildings or the pool
        var nx = c.x + c.vx * dt, ny = c.y + c.vy * dt;
        if (walkable(nx, c.y)) c.x = nx; else c.vx = 0;
        if (walkable(c.x, ny)) c.y = ny; else c.vy = 0;
        c.bob += dt * 6;
      } else { c.x = c.tx; c.y = c.ty; c.vx *= 0.8; c.vy *= 0.8; }
      if (c.speaking && now - c.bubbleAt > 7500) { c.speaking = false; c.bubble = null; c.returnAt = now + 800; }
      if (!c.speaking && c.returnAt && now > c.returnAt) { c.tx = c.home[0]; c.ty = c.home[1]; c.returnAt = 0; c.activity = ''; c.vehicle = ''; c.running = false; }
      if (!c.speaking && !c.returnAt) {
        c.idle -= dt;
        if (c.idle <= 0 && Math.hypot(c.tx - c.x, c.ty - c.y) < 0.1) {
          // a calm town: mostly stand and watch, sometimes rest at a seat, rarely amble a short way
          var roll = Math.random();
          if (roll < 0.5) {                                   // linger where they are
            c.idle = 5 + Math.random() * 7;
          } else if (roll < 0.78 && S.seats && S.seats.length) { // go sit down for a while
            var st = S.seats[Math.floor(Math.random() * S.seats.length)];
            if (walkable(st[0], st[1])) { c.tx = st[0]; c.ty = st[1]; }
            c.idle = 7 + Math.random() * 6;
          } else {                                            // gentle amble to a nearby tile
            for (var k = 0; k < 8; k++) { var ax = Math.round(c.x + (Math.random() * 4 - 2)), ay = Math.round(c.y + (Math.random() * 4 - 2)); if (walkable(ax, ay)) { c.tx = ax; c.ty = ay; break; } }
            c.idle = 4 + Math.random() * 5;
          }
          c.running = false;   // never run while idle — only when actually reacting to an event
        }
      }
    }

    // ---------- loop ----------
    var last = performance.now();
    function frame(now) {
      var dt = Math.min(0.05, (now - last) / 1000); last = now;
      var rect = canvas.getBoundingClientRect();
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
      var sky = ctx.createLinearGradient(0, 0, 0, rect.height);
      sky.addColorStop(0, '#161038'); sky.addColorStop(0.45, '#2a1c52'); sky.addColorStop(1, '#0b1e16');
      ctx.fillStyle = sky; ctx.fillRect(0, 0, rect.width, rect.height);
      if (!S.W) { requestAnimationFrame(frame); return; }
      for (var s = 0; s <= (S.W.cols + S.W.rows); s++) for (var gx = 0; gx < S.W.cols; gx++) { var gy = s - gx; if (gy < 0 || gy >= S.W.rows) continue; drawTile(gx, gy); }
      S.chars.forEach(function (c) { step(c, dt, now); });
      (S.amb || []).forEach(function (a) { stepAmbient(a, dt); });
      (S.cars || []).forEach(function (c) { stepCar(c, dt); });
      var ents = [];
      (S.W.props || []).forEach(function (p) { var k = (p.gy + (p.d || 1)) + (p.gx + (p.w || 1)); ents.push({ d: k - 0.6, f: function () { drawProp(p, now); } }); });
      S.W.buildings.forEach(function (b) { ents.push({ d: (b.gx + b.gy) + (b.w + b.d) - 0.5, f: function () { drawBuilding(b, now); } }); });
      (S.W.trees || []).forEach(function (t) { ents.push({ d: t[0] + t[1] + 0.4, f: function () { drawTree(t); } }); });
      (S.cars || []).forEach(function (c) { var gx = (c.axis === 'h') ? c.pos : c.line + 0.5, gy = (c.axis === 'h') ? c.line + 0.5 : c.pos; ents.push({ d: gx + gy + 0.45, f: function () { drawCar(c); } }); });
      (S.amb || []).forEach(function (a) { ents.push({ d: a.x + a.y + 0.45, f: function () { drawAmbient(a); } }); });
      S.chars.forEach(function (c) { ents.push({ d: c.x + c.y + 0.5, f: function () { drawChar(c, now); } }); });
      ents.sort(function (a, b) { return a.d - b.d; }); ents.forEach(function (e) { e.f(); });
      for (var i = S.waves.length - 1; i >= 0; i--) {
        var w = S.waves[i]; w.t += dt; var rr2 = w.t * 560 * S.scale, al = Math.max(0, 0.7 - w.t);
        if (al <= 0) { S.waves.splice(i, 1); continue; }
        ctx.strokeStyle = 'rgba(56,232,255,' + al + ')'; ctx.lineWidth = 2.4 * S.scale;
        ctx.beginPath(); ctx.ellipse(w.x, w.y, rr2, rr2 * 0.5, 0, 0, 7); ctx.stroke();
      }
      requestAnimationFrame(frame);
    }

    function applyReactions(d) {
      if (!d || !d.reactions || !S.W) return;
      if (!d.silent) {
        var pc = S.W.plaza_center || [S.W.cols / 2, S.W.rows / 2]; var p = iso(pc[0], pc[1]); S.waves.push({ x: p.x, y: p.y, t: 0 });
      }
      d.reactions.forEach(function (r) {
        var c = S.chars.find(function (x) { return x.name === r.name; }); if (!c) return;
        c.moodEmoji = r.moodEmoji || c.moodEmoji || '';
        if (r.text) { c.bubble = r.text; c.bubbleAt = performance.now(); c.speaking = true; c.returnAt = 0; }
        c.activity = r.activity || c.activity || ''; c.vehicle = r.vehicle || ''; c.running = !!r.running;
        if (r.target) { c.tx = r.target[0]; c.ty = r.target[1]; }
      });
    }

    function poll() {
      var wj = txt('#tw-world');
      if (wj && wj !== S.raw) { try { var W = JSON.parse(wj); S.raw = wj; loadWorld(W); } catch (e) { } }
      var rj = txt('#tw-reactions');
      if (rj) { try { var d = JSON.parse(rj); if (d.ts && d.ts !== S.lastTs) { S.lastTs = d.ts; applyReactions(d); } } catch (e) { } }
    }

    return {
      start: function () { window.TINYWORLD = { applyReactions: applyReactions }; requestAnimationFrame(frame); setInterval(poll, 140); poll(); }
    };
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
