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
  // One dataLayer event per booking, call, text, directions or email click:
  //   {event: 'bb_book'|'bb_call'|'bb_text'|'bb_directions'|'bb_email', bb_salon: 'yonge'|'bridlewood',
  //    bb_link: <href>, bb_placement: <where on the page>}
  // Google Tag Manager (GTM-M6WHQ2D5, production build only) turns these into GA4 events and Ads conversions.
  const SALON = [
    [/e0fzhnga|4164847788|4374344884|3430|beautiquebar\.yonge@/i, 'yonge'],
    [/bkuolnwc|m7weksrj|pId=32159|6477705232|Bridlewood|2900|beautiquebar88@/i, 'bridlewood'],
  ];
  // Page context: on a salon page, a link without its own salon (the shared email) belongs to that salon.
  const PAGE_SALON = /^\/(locations\/)?yonge\/?$/.test(location.pathname) ? 'yonge'
    : /^\/(locations\/)?warden\/?$/.test(location.pathname) ? 'bridlewood' : null;
  const PLACES = [
    ['.book-dialog', 'booking-dialog'], ['.menu-panel', 'mobile-menu'], ['.site-header', 'header'],
    ['.site-footer', 'footer'], ['.pg-hero', 'hero'], ['.opening', 'hero'], ['.facts', 'salon-details'],
    ['.facts-sec', 'salon-details'], ['.book-pair', 'prices'], ['.menu', 'menu'], ['.salon', 'salon-card'], ['.close, .close--inner', 'closing'],
    ['.ct-col', 'contact'], ['.contact', 'contact'], ['.post-body', 'article'],
  ];
  const placement = a => {
    const tagged = a.closest('[data-placement]');
    if (tagged) return tagged.dataset.placement;
    for (const [sel, name] of PLACES) if (a.closest(sel)) return name;
    const sec = a.closest('section[id]');
    return sec ? sec.id : 'body';
  };
  document.addEventListener('click', ev => {
    const a = ev.target.closest && ev.target.closest('a[href]');
    if (!a) return;
    const href = a.getAttribute('href');
    const kind = /fresha\.com/i.test(href) ? 'book' : /^tel:/i.test(href) ? 'call' : /^sms:/i.test(href) ? 'text'
      : /google\.[^/]+\/maps/i.test(href) ? 'directions' : /^mailto:/i.test(href) ? 'email' : null;
    if (!kind) return;
    const hit = SALON.find(([re]) => re.test(href));
    (window.dataLayer = window.dataLayer || []).push({
      event: 'bb_' + kind, bb_salon: hit ? hit[1] : (PAGE_SALON || 'unknown'), bb_link: href, bb_placement: placement(a),
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
