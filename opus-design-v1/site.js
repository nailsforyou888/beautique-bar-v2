/* Beautique Bar — shared page script.
   Everywhere: mobile menu. Inner pages only (the homepage's opus.js already does these):
   section-aware header, booking dialog, photography-notes toggle. Native scroll only. */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const header = $('.site-header');
  const isHome = !!$('.opening');

  // ---- Mobile menu ------------------------------------------------------------------------
  const btn = $('.menu-btn'), panel = $('#menu-panel');
  if (btn && panel) {
    let lastTone = null;
    const setOpen = open => {
      btn.setAttribute('aria-expanded', open);
      panel.hidden = !open;
      document.documentElement.classList.toggle('menu-open', open);
      document.body.style.overflow = open ? 'hidden' : '';
      btn.querySelector('.menu-label').textContent = open ? 'Close' : 'Menu';
      if (open) { lastTone = header.dataset.bg; panel.querySelector('a').focus(); }
      else if (lastTone) { header.dataset.bg = lastTone; }
    };
    btn.addEventListener('click', () => setOpen(btn.getAttribute('aria-expanded') !== 'true'));
    document.addEventListener('keydown', ev => {
      if (ev.key === 'Escape' && !panel.hidden) { setOpen(false); btn.focus(); }
    });
    panel.addEventListener('click', ev => { if (ev.target.closest('a')) setOpen(false); });
    matchMedia('(min-width: 901px)').addEventListener('change', m => { if (m.matches) setOpen(false); });
  }

  if (isHome) return;

  // ---- Section-aware header ---------------------------------------------------------------
  const toned = $$('[data-tone]');
  const footer = $('.site-footer');
  let queued = false;
  function draw() {
    queued = false;
    let bg = 'light';
    const probe = 40;
    const hit = toned.find(s => { const r = s.getBoundingClientRect(); return r.top <= probe && r.bottom > probe; });
    if (hit) bg = hit.dataset.tone;
    if (footer && footer.getBoundingClientRect().top <= probe) bg = 'dark';
    if (!document.documentElement.classList.contains('menu-open') && header.dataset.bg !== bg) header.dataset.bg = bg;
    header.classList.toggle('is-solid', scrollY > 30);
  }
  const schedule = () => { if (!queued) { queued = true; requestAnimationFrame(draw); } };
  addEventListener('scroll', schedule, { passive: true });
  addEventListener('resize', schedule);
  draw();

  // ---- Booking dialog ---------------------------------------------------------------------
  const dlg = $('.book-dialog'); let opener = null;
  if (dlg) {
    $$('[data-book]').forEach(b => b.addEventListener('click', () => { opener = b; dlg.showModal(); }));
    $('.dlg-close', dlg).addEventListener('click', () => dlg.close());
    dlg.addEventListener('close', () => opener && opener.focus());
    dlg.addEventListener('click', ev => {
      if (ev.target !== dlg) return;
      const r = dlg.getBoundingClientRect();
      if (ev.clientX < r.left || ev.clientX > r.right || ev.clientY < r.top || ev.clientY > r.bottom) dlg.close();
    });
  }

  // ---- Photography notes toggle -----------------------------------------------------------
  const notes = $('.notes-toggle');
  if (notes) {
    const set = on => { document.body.classList.toggle('show-notes', on); notes.setAttribute('aria-pressed', on); };
    notes.addEventListener('click', () => set(!document.body.classList.contains('show-notes')));
    if (/[?&]notes\b/.test(location.search)) set(true);
  }
})();
