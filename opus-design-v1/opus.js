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
  const opening = $('.opening');
  const o = {
    win: $('.window'), salon: $('.win-salon'), hands: $('.win-hands'), veil: $('.veil'),
    dl: $('.door-l'), dr: $('.door-r'), seam: $('.seam'),
    kicker: $('.kicker'), tOut: $('.t-out'), tIn: $('.t-in'), come: $('.come-in'),
    rl: $('.r-left'), rr: $('.r-right'), cue: $('.cue')
  };
  const room = $('.room'), roomPhoto = $('.room-photo'), roomImg = $('.room-photo img'),
        roomCopy = $('.room-copy'), roomWords = $('.room-words');

  const progress = el => {
    const r = el.getBoundingClientRect();
    return clamp(-r.top / Math.max(1, el.offsetHeight - innerHeight));
  };

  let openingBgDark = true;

  function drawOpening(p) {
    const vw = innerWidth / 100, vh = innerHeight / 100;
    // 1 · the seam appears, doors part
    const seamIn = range(p, .015, .09), split = range(p, .07, .40);
    o.seam.style.transform = `scaleY(${seamIn})`;
    o.seam.style.opacity = 1 - range(p, .12, .2);
    const push = 1 + .05 * split;
    o.dl.style.transform = `translate3d(${-101 * split}%,0,0) scale(${push})`;
    o.dr.style.transform = `translate3d(${101 * split}%,0,0) scale(${push})`;
    o.dl.style.transformOrigin = '100% 50%'; o.dr.style.transformOrigin = '0 50%';
    o.cue.style.opacity = .85 * (1 - range(p, 0, .05));
    o.kicker.style.opacity = 1 - range(p, .03, .14);

    // "Outside, the city." belongs to the outside — it leaves with the left door.
    o.tOut.style.transform = `translate3d(${-52 * vw * split}px,0,0)`;
    o.tOut.style.opacity = 1 - range(p, .16, .36);
    // "Inside, your time." belongs to the inside — it stays, then gives way.
    const inOut = range(p, .40, .49);
    o.tIn.style.opacity = 1 - inOut;
    o.tIn.style.transform = `translate3d(0,${-30 * inOut}px,0)`;

    // 2 · the room: lights come up, lens settles
    o.salon.style.transform = `scale(${lerp(1.2, 1, range(p, .07, .62))})`;
    const come = range(p, .45, .53) * (1 - range(p, .58, .64));
    o.come.style.opacity = come;
    o.come.style.transform = `translate3d(0,${lerp(24, 0, range(p, .45, .55))}px,0)`;

    // 3 · the room contracts into a window on warm stone
    const w = range(p, .60, .82);
    const ins = `inset(${w * 12}vh ${w * 35.5}vw ${w * 12}vh ${w * 35.5}vw)`;
    o.win.style.clipPath = ins;
    o.win.style.webkitClipPath = ins;
    o.veil.style.opacity = lerp(.5, .18, split) * (1 - range(p, .62, .8));
    const h = range(p, .70, .86);
    o.hands.style.opacity = h;
    o.hands.style.transform = `scale(${lerp(1.14, 1, range(p, .70, .98))})`;

    // 4 · the ritual is spoken either side of the window
    const r = range(p, .78, .93);
    o.rl.style.opacity = r; o.rr.style.opacity = r;
    o.rl.style.transform = `translateY(-50%) translate3d(${lerp(-26, 0, r)}px,0,0)`;
    o.rr.style.transform = `translateY(-50%) translate3d(${lerp(26, 0, r)}px,0,0)`;

    openingBgDark = w < .45;
  }

  function drawRoom(p) {
    const a = range(p, .02, .55);
    const ins = `inset(${lerp(20, 0, a)}vh ${lerp(41, 0, a)}vw ${lerp(20, 0, a)}vh ${lerp(41, 0, a)}vw)`;
    roomPhoto.style.clipPath = ins; roomPhoto.style.webkitClipPath = ins;
    roomImg.style.transform = `scale(${lerp(1.3, 1.02, a)}) translate3d(0,${lerp(0, -2, p)}%,0)`;
    const c = range(p, .5, .72);
    roomCopy.style.opacity = c;
    roomCopy.style.transform = `translate3d(0,${lerp(24, 0, c)}px,0)`;
    roomWords.style.opacity = range(p, .6, .8);
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
      drawRoom(progress(room));
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
      [...Object.values(o), roomPhoto, roomImg, roomCopy, roomWords].forEach(el => el && el.removeAttribute('style'));
    }
    schedule();
  }
  reduced.addEventListener('change', applyMotionPreference);

  // Quiet one-time reveals
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('in-view'); io.unobserve(e.target); }
  }), { threshold: .15 });
  $$('.reveal, .story').forEach(el => io.observe(el));

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
