/* Beautique Bar — opus-design-v1
   Native scroll only. Every scroll-linked value is a pure function of scroll position,
   so scrolling back up plays the scene in reverse exactly. */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const smooth = x => x * x * (3 - 2 * x);
  const range = (p, a, b) => smooth(clamp((p - a) / (b - a)));
  const lerp = (a, b, t) => a + (b - a) * t;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');

  const header = $('.site-header');
  const opening = $('.opening'), stage = $('.stage');
  const o = {
    win: $('.window'), salon: $('.win-salon'), hands: $('.win-hands'), veil: $('.veil'),
    dl: $('.door-l'), dr: $('.door-r'), seam: $('.seam'),
    kicker: $('.kicker'), tOut: $('.t-out'), tIn: $('.t-in'), come: $('.come-in'),
    rl: $('.r-left'), rr: $('.r-right'), cue: $('.cue')
  };

  const progress = el => {
    const r = el.getBoundingClientRect();
    return clamp(-r.top / Math.max(1, el.offsetHeight - innerHeight));
  };

  let openingBgDark = true;

  /* Opening timeline (p = 0…1 across the pinned scene)
     0.00–0.08  read: headline alone, nothing moves
     0.08–0.36  doors part; headline clears early (gone by .26)
     0.26–0.40  the salon, clean — no copy
     0.40–0.60  "Come in. Switch off." surfaces and leaves
     0.60–0.64  the salon again, a beat to register "we're inside"
     0.64–0.82  the room contracts into a window; hands dissolve in
     0.80–0.90  "Your everyday / beauty ritual.", then holds to 1.00          */
  function drawOpening(p) {
    const vw = innerWidth / 100;
    const seamIn = range(p, .03, .09), split = range(p, .08, .36);
    o.seam.style.transform = `scaleY(${seamIn})`;
    o.seam.style.opacity = 1 - range(p, .12, .18);
    const push = 1 + .05 * split;
    o.dl.style.transform = `translate3d(${-101 * split}%,0,0) scale(${push})`;
    o.dr.style.transform = `translate3d(${101 * split}%,0,0) scale(${push})`;
    o.dl.style.transformOrigin = '100% 50%'; o.dr.style.transformOrigin = '0 50%';
    o.cue.style.opacity = .85 * (1 - range(p, 0, .04));
    o.kicker.style.opacity = 1 - range(p, .05, .12);

    // "Outside, the city." belongs to the outside — it leaves with the left door, and fades early.
    o.tOut.style.transform = `translate3d(${-52 * vw * split}px,0,0)`;
    o.tOut.style.opacity = 1 - range(p, .10, .19);
    // "Inside, your time." stays a moment longer, then clears so the room is seen on its own.
    const inOut = range(p, .15, .26);
    o.tIn.style.opacity = 1 - inOut;
    o.tIn.style.transform = `translate3d(0,${-24 * inOut}px,0)`;

    o.salon.style.transform = `scale(${lerp(1.2, 1, range(p, .08, .6))})`;
    const come = range(p, .40, .47) * (1 - range(p, .54, .60));
    o.come.style.opacity = come;
    o.come.style.transform = `translate3d(0,${lerp(22, 0, range(p, .40, .49))}px,0)`;

    const w = range(p, .64, .82);
    const ins = `inset(${w * 12}vh ${w * 35.5}vw ${w * 12}vh ${w * 35.5}vw)`;
    o.win.style.clipPath = ins; o.win.style.webkitClipPath = ins;
    // brighter once open; a touch darker only while copy sits on the photo
    o.veil.style.opacity = (lerp(.5, .12, split) + .2 * come + .22 * (1 - inOut) * split) * (1 - range(p, .64, .78));
    const h = range(p, .72, .86);
    o.hands.style.opacity = h;
    o.hands.style.transform = `scale(${lerp(1.12, 1, range(p, .72, 1))})`;

    const r = range(p, .80, .90);
    o.rl.style.opacity = r; o.rr.style.opacity = r;
    o.rl.style.transform = `translateY(-50%) translate3d(${lerp(-24, 0, r)}px,0,0)`;
    o.rr.style.transform = `translateY(-50%) translate3d(${lerp(24, 0, r)}px,0,0)`;

    stage.style.setProperty('--scrim', (1 - range(p, .64, .74)).toFixed(3));
    openingBgDark = w < .45;
  }

  // The salons: one quiet parallax on the comfort detail — the only scroll-linked motion after the opening.
  const room = $('.room'), roomDetail = $('.room-detail');
  function drawRoom() {
    const r = room.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight) return;
    const t = clamp((innerHeight - r.top) / (innerHeight + r.height)); // 0 → 1 while on screen
    roomDetail.style.transform = `translate3d(0,${lerp(50, -50, t)}px,0)`;
  }

  // Section-aware header: tone follows whatever sits beneath it.
  const toned = $$('[data-tone]');
  function drawHeader() {
    let bg = 'dark';
    const openR = opening.getBoundingClientRect();
    if (openR.bottom > 40) {
      bg = reduced.matches ? ($('.ritual').getBoundingClientRect().top <= 40 ? 'light' : 'dark') : (openingBgDark ? 'dark' : 'light');
    } else {
      for (const s of toned) {
        const r = s.getBoundingClientRect();
        if (r.top <= 40 && r.bottom > 40) { bg = s.dataset.tone; break; }
      }
      if (!toned.some(s => { const r = s.getBoundingClientRect(); return r.top <= 40 && r.bottom > 40; })) bg = 'dark';
    }
    if (header.dataset.bg !== bg) header.dataset.bg = bg;
    header.classList.toggle('is-solid', scrollY > 40 && openR.bottom <= 40);
  }

  let queued = false;
  function frame() {
    queued = false;
    if (!reduced.matches) {
      drawOpening(progress(opening));
      drawRoom();
    }
    drawHeader();
  }
  const schedule = () => { if (!queued) { queued = true; requestAnimationFrame(frame); } };
  addEventListener('scroll', schedule, { passive: true });
  addEventListener('resize', schedule);
  addEventListener('pageshow', schedule);
  document.fonts && document.fonts.ready.then(schedule);

  function applyMotionPreference() {
    if (reduced.matches) {
      [...Object.values(o), roomDetail, stage].forEach(el => el && el.removeAttribute('style'));
    }
    schedule();
  }
  reduced.addEventListener('change', applyMotionPreference);

  // Quiet one-time reveals
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('in-view'); io.unobserve(e.target); }
  }), { threshold: .15 });
  $$('.reveal, .story, .room-main').forEach(el => io.observe(el));

  // Nails index follows the story in view
  const stories = $$('.story'), idx = $$('.nail-index li');
  const storyIO = new IntersectionObserver(es => {
    es.forEach(e => { if (e.isIntersecting) idx.forEach((li, i) => li.classList.toggle('is-active', i === +e.target.dataset.i)); });
  }, { rootMargin: '-45% 0px -45% 0px' });
  stories.forEach(s => storyIO.observe(s));

  // Beyond nails: list drives one masked photograph (scroll, hover or focus)
  const rows = $$('.service'), photos = $$('.service-photo img'), count = $('.sp-count');
  let current = 0;
  function selectService(i) {
    if (i === current) return;
    photos.forEach((im, k) => { im.classList.toggle('was-active', k === current); im.classList.toggle('is-active', k === i); });
    rows.forEach((r, k) => r.classList.toggle('is-active', k === i));
    count.textContent = String(i + 1).padStart(2, '0');
    current = i;
  }
  const rowIO = new IntersectionObserver(es => {
    es.forEach(e => { if (e.isIntersecting) selectService(+e.target.dataset.i); });
  }, { rootMargin: '-40% 0px -50% 0px' });
  rows.forEach((r, i) => {
    rowIO.observe(r);
    r.addEventListener('mouseenter', () => selectService(i));
    r.addEventListener('focusin', () => selectService(i));
  });

  // Booking dialog
  const dlg = $('.book-dialog'); let opener = null;
  $$('[data-book]').forEach(b => b.addEventListener('click', () => { opener = b; dlg.showModal(); }));
  $('.dlg-close', dlg).addEventListener('click', () => dlg.close());
  dlg.addEventListener('close', () => opener && opener.focus());
  dlg.addEventListener('click', e => {
    if (e.target !== dlg) return;
    const r = dlg.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) dlg.close();
  });

  // Review aid: overlay photography briefs on every temporary image
  const notes = $('.notes-toggle');
  const setNotes = on => { document.body.classList.toggle('show-notes', on); notes.setAttribute('aria-pressed', on); };
  notes.addEventListener('click', () => setNotes(!document.body.classList.contains('show-notes')));
  if (/[?&]notes\b/.test(location.search)) setNotes(true);

  applyMotionPreference();
})();
