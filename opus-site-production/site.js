/* Beautique Bar — shared page script.
   Everywhere: mobile menu and photo lightbox. Inner pages only (the homepage's opus.js already does these):
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

  // ---- Lightbox for [data-lightbox] links (gallery + work strips, all pages) --------------------
  const lbLinks = $$('a[data-lightbox]');
  if (lbLinks.length) {
    const d = document.createElement('dialog');
    d.className = 'lightbox';
    d.setAttribute('aria-label', 'Photo viewer');
    d.innerHTML = '<p aria-live="polite"></p><button type="button" class="lb-btn lb-close" aria-label="Close">×</button>' +
      '<button type="button" class="lb-btn lb-prev" aria-label="Previous photo">←</button><button type="button" class="lb-btn lb-next" aria-label="Next photo">→</button>';
    document.body.appendChild(d);
    const im = new Image(), cap = d.querySelector('p');
    im.decoding = 'async';
    let idx = 0, from = null;
    const show = i => {
      idx = (i + lbLinks.length) % lbLinks.length;
      const a = lbLinks[idx];
      im.src = a.getAttribute('href'); im.alt = a.querySelector('img').alt;
      if (!im.isConnected) d.prepend(im);
      cap.textContent = `${a.dataset.lightbox} · ${idx + 1} / ${lbLinks.length}`;
    };
    lbLinks.forEach((a, i) => a.addEventListener('click', ev => {
      if (ev.metaKey || ev.ctrlKey || ev.shiftKey) return;
      ev.preventDefault(); from = a; show(i); d.showModal(); d.querySelector('.lb-close').focus();
    }));
    d.querySelector('.lb-close').addEventListener('click', () => d.close());
    d.querySelector('.lb-prev').addEventListener('click', () => show(idx - 1));
    d.querySelector('.lb-next').addEventListener('click', () => show(idx + 1));
    d.addEventListener('keydown', ev => { if (ev.key === 'ArrowLeft') show(idx - 1); if (ev.key === 'ArrowRight') show(idx + 1); });
    d.addEventListener('click', ev => { if (ev.target === d) d.close(); });
    d.addEventListener('close', () => { from && from.focus(); });
  }

  // ---- Conversion events (all pages) ----------------------------------------------------------
  // Pushes a dataLayer event for every booking, call, text, directions and email click, tagged
  // with the salon. Google Tag Manager (added only on the production build) can turn these into
  // GA4 events and Google Ads conversions per salon. Without GTM this is a harmless no-op.
  const SALON = [
    [/e0fzhnga|4164847788|4374344884|3430/i, 'yonge'],
    [/m7weksrj|pId=32159|6477705232|Bridlewood|2900/i, 'bridlewood'],
  ];
  document.addEventListener('click', ev => {
    const a = ev.target.closest && ev.target.closest('a[href]');
    if (!a) return;
    const href = a.getAttribute('href');
    const kind = /fresha\.com/i.test(href) ? 'book' : /^tel:/i.test(href) ? 'call' : /^sms:/i.test(href) ? 'text'
      : /google\.[^/]+\/maps/i.test(href) ? 'directions' : /^mailto:/i.test(href) ? 'email' : null;
    if (!kind) return;
    const hit = SALON.find(([re]) => re.test(href));
    (window.dataLayer = window.dataLayer || []).push({
      event: 'bb_' + kind, bb_salon: hit ? hit[1] : 'unknown', bb_link: href,
      bb_placement: (a.closest('[class]') || a).className.split(' ')[0] || 'link',
    });
  }, true);

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
