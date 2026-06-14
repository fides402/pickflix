/* Kiwi Fast Nav – YouTube Turbo | content script */

(function () {
  'use strict';

  const DEFAULT_CFG = {
    skipAds: true,
    removeBloat: true,
    touchGestures: true,
    autoDismissConsent: true,
    autoTheater: false,
    skipCountdown: true,
    hideShortsRedirect: true,
    seekSeconds: 10,
  };

  let cfg = { ...DEFAULT_CFG };

  chrome.storage.sync.get(DEFAULT_CFG, (saved) => {
    cfg = { ...DEFAULT_CFG, ...saved };
    init();
  });

  function qs(sel, root = document) { return root.querySelector(sel); }
  function qsa(sel, root = document) { return [...root.querySelectorAll(sel)]; }
  function click(el) { if (el) el.click(); }
  function getPlayer() { return qs('video') || qs('#movie_player video'); }

  // ── Ad Skipper ───────────────────────────────────────────────────────────
  const AD_SKIP_SELECTORS = [
    '.ytp-skip-ad-button',
    '.ytp-ad-skip-button',
    '.ytp-ad-skip-button-modern',
    'button[class*="skip"]',
  ];

  const AD_OVERLAY_SELECTORS = [
    '.ytp-ad-overlay-container',
    '.ytp-ad-text-overlay',
    '.ytp-ad-image-overlay',
    '#masthead-ad',
    '.ytd-banner-promo-renderer',
    'ytd-action-companion-ad-renderer',
    'ytd-display-ad-renderer',
    'ytd-promoted-sparkles-web-renderer',
    'ytd-rich-item-renderer[is-ad]',
    'ytd-ad-slot-renderer',
    'ytd-statement-banner-renderer',
    'tp-yt-paper-dialog[aria-label*="sponsor"]',
  ];

  function skipAd() {
    for (const sel of AD_SKIP_SELECTORS) {
      const btn = qs(sel);
      if (btn) { click(btn); break; }
    }

    const adBadge = qs('.ytp-ad-simple-ad-badge, .ytp-ad-duration-remaining');
    if (adBadge) {
      const vid = getPlayer();
      if (vid && vid.duration && isFinite(vid.duration)) {
        vid.currentTime = vid.duration;
      }
    }

    const adPlaying = qs('.ad-showing');
    const vid = getPlayer();
    if (vid) {
      if (adPlaying) vid.muted = true;
      else if (vid.muted && !userMuted) vid.muted = false;
    }

    for (const sel of AD_OVERLAY_SELECTORS) {
      qsa(sel).forEach(el => el.remove());
    }
  }

  let userMuted = false;
  document.addEventListener('volumechange', () => {
    const vid = getPlayer();
    if (vid && !qs('.ad-showing')) userMuted = vid.muted;
  }, true);

  // ── Bloat Remover ────────────────────────────────────────────────────────
  function injectBloatStyle() {
    if (qs('#fn-bloat-style')) return;
    const style = document.createElement('style');
    style.id = 'fn-bloat-style';
    style.textContent = `
      #secondary { display: none !important; }
      ytd-rich-shelf-renderer,
      ytd-shelf-renderer { display: none !important; }
      .ytp-ce-element { display: none !important; }
      .ytp-cards-teaser { display: none !important; }
      ytd-merch-shelf-renderer { display: none !important; }
      ytd-ticket-shelf-renderer { display: none !important; }
      ytd-channel-featured-content-renderer { display: none !important; }
      html { scroll-behavior: smooth !important; }
      * { transition-duration: 0.1s !important; }
    `;
    document.head.appendChild(style);
  }

  // ── Shorts → full video ──────────────────────────────────────────────────
  function expandShortsToFull() {
    if (location.href.includes('/shorts/')) {
      const id = location.href.split('/shorts/')[1].split('?')[0].split('/')[0];
      if (id) location.replace(`https://www.youtube.com/watch?v=${id}`);
    }
  }

  // ── Consent Dismisser ────────────────────────────────────────────────────
  const CONSENT_TEXTS = [
    'Accetta tutto', 'Accept all', 'Accetta', 'Accept',
    'Agree', 'OK', 'Continua', 'Continue without',
  ];

  function dismissConsent() {
    qsa('form[action*="consent"]').forEach(f => {
      const btn = [...f.querySelectorAll('button')].find(b =>
        CONSENT_TEXTS.some(t => b.textContent.trim().startsWith(t))
      );
      if (btn) click(btn);
    });
    qsa('tp-yt-paper-dialog, ytd-consent-bump-v2-lightbox, .ytd-consent-bump-v2-lightbox').forEach(d => {
      const btn = [...d.querySelectorAll('button, [role="button"]')].find(b =>
        CONSENT_TEXTS.some(t => b.textContent.trim().includes(t))
      );
      if (btn) click(btn);
    });
  }

  // ── Autoplay Countdown Skipper ───────────────────────────────────────────
  function skipCountdown() {
    const countdown = qs('.ytp-autonav-endscreen-upnext-countdown-overlay');
    if (countdown) click(qs('.ytp-autonav-endscreen-upnext-button'));
  }

  // ── Theater Mode ─────────────────────────────────────────────────────────
  function enableTheater() {
    const btn = qs('.ytp-size-button, button[data-tooltip-target-id="ytp-size-button"]');
    if (btn && !qs('ytd-watch-flexy[theater]')) setTimeout(() => click(btn), 600);
  }

  // ── Touch Gesture Engine ─────────────────────────────────────────────────
  function initTouchGestures() {
    const playerArea = qs('#player, #movie_player, .html5-video-player');
    if (!playerArea || playerArea._fnGestures) return;
    playerArea._fnGestures = true;

    let touchStartX = 0, touchStartY = 0, touchStartTime = 0;
    let lastTapTime = 0, lastTapX = 0;
    const DBL_TAP_MS = 300;
    const DBL_TAP_PX = 80;
    const SWIPE_MIN = 40;

    let feedbackTimeout;
    function showFeedback(text) {
      let fb = qs('#fn-gesture-feedback');
      if (!fb) {
        fb = document.createElement('div');
        fb.id = 'fn-gesture-feedback';
        document.body.appendChild(fb);
      }
      fb.textContent = text;
      fb.classList.add('fn-show');
      clearTimeout(feedbackTimeout);
      feedbackTimeout = setTimeout(() => fb.classList.remove('fn-show'), 700);
    }

    playerArea.addEventListener('touchstart', (e) => {
      const t = e.touches[0];
      touchStartX = t.clientX;
      touchStartY = t.clientY;
      touchStartTime = Date.now();
    }, { passive: true });

    playerArea.addEventListener('touchend', (e) => {
      const t = e.changedTouches[0];
      const dx = t.clientX - touchStartX;
      const dy = t.clientY - touchStartY;
      const dt = Date.now() - touchStartTime;
      const vid = getPlayer();

      if (Math.abs(dx) < SWIPE_MIN && Math.abs(dy) < SWIPE_MIN && dt < 300) {
        const now = Date.now();
        const isDoubleTap =
          now - lastTapTime < DBL_TAP_MS &&
          Math.abs(t.clientX - lastTapX) < DBL_TAP_PX;

        if (isDoubleTap && vid) {
          const w = playerArea.getBoundingClientRect().width;
          if (t.clientX < w / 2) {
            vid.currentTime = Math.max(0, vid.currentTime - cfg.seekSeconds);
            showFeedback(`⏪ −${cfg.seekSeconds}s`);
          } else {
            vid.currentTime = Math.min(vid.duration || Infinity, vid.currentTime + cfg.seekSeconds);
            showFeedback(`⏩ +${cfg.seekSeconds}s`);
          }
          lastTapTime = 0;
        } else {
          lastTapTime = now;
          lastTapX = t.clientX;
        }
        return;
      }

      if (Math.abs(dx) > SWIPE_MIN && Math.abs(dx) > Math.abs(dy) * 1.5 && vid) {
        const seekAmt = Math.round((dx / playerArea.getBoundingClientRect().width) * 60);
        vid.currentTime = Math.max(0, Math.min(vid.duration || Infinity, vid.currentTime + seekAmt));
        showFeedback(seekAmt > 0 ? `⏩ +${seekAmt}s` : `⏪ ${seekAmt}s`);
        return;
      }

      if (Math.abs(dy) > SWIPE_MIN && Math.abs(dy) > Math.abs(dx) * 1.5 && vid) {
        const rect = playerArea.getBoundingClientRect();
        if (touchStartX > rect.left + rect.width / 2) {
          const delta = -(dy / rect.height) * 0.5;
          vid.volume = Math.max(0, Math.min(1, vid.volume + delta));
          showFeedback(`🔊 ${Math.round(vid.volume * 100)}%`);
        } else {
          const bDelta = -(dy / rect.height) * 0.5;
          const currentBr = parseFloat(vid.style.filter?.match(/brightness\(([^)]+)\)/)?.[1] || 1);
          const newBr = Math.max(0.1, Math.min(2, currentBr + bDelta));
          vid.style.filter = `brightness(${newBr.toFixed(2)})`;
          showFeedback(`☀️ ${Math.round(newBr * 100)}%`);
        }
      }
    }, { passive: true });
  }

  // ── MutationObserver ─────────────────────────────────────────────────────
  function startObserver() {
    const obs = new MutationObserver(() => {
      if (cfg.skipAds) skipAd();
      if (cfg.autoDismissConsent) dismissConsent();
      if (cfg.skipCountdown) skipCountdown();
    });
    obs.observe(document.body, { childList: true, subtree: true });
  }

  // ── Navigation (YouTube SPA) ─────────────────────────────────────────────
  function onNavigate() {
    if (cfg.hideShortsRedirect) expandShortsToFull();
    setTimeout(() => {
      if (cfg.autoTheater && isWatchPage()) enableTheater();
      if (cfg.touchGestures) initTouchGestures();
    }, 1000);
  }

  function isWatchPage() { return location.pathname.startsWith('/watch'); }

  // ── Init ─────────────────────────────────────────────────────────────────
  function init() {
    if (cfg.hideShortsRedirect) expandShortsToFull();
    if (cfg.removeBloat) injectBloatStyle();
    if (cfg.autoDismissConsent) dismissConsent();
    if (cfg.skipAds) skipAd();

    startObserver();

    setTimeout(() => {
      if (cfg.touchGestures) initTouchGestures();
      if (cfg.autoTheater && isWatchPage()) enableTheater();
    }, 1200);

    document.addEventListener('yt-navigate-finish', onNavigate);
    document.addEventListener('yt-page-data-updated', () => {
      if (cfg.skipAds) skipAd();
    });
  }
})();
