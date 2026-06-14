/* Kiwi Fast Nav – YouTube Turbo | content script */

(function () {
  'use strict';

  // ── Config loaded from storage ───────────────────────────────────────────
  const DEFAULT_CFG = {
    skipAds: true,
    autoSpeed: false,
    defaultSpeed: 1,
    removeBloat: true,
    touchGestures: true,
    autoDismissConsent: true,
    autoTheater: false,
    autoPip: false,
    skipCountdown: true,
    hideShortsRedirect: true,
    seekSeconds: 10,
  };

  let cfg = { ...DEFAULT_CFG };

  chrome.storage.sync.get(DEFAULT_CFG, (saved) => {
    cfg = { ...DEFAULT_CFG, ...saved };
    init();
  });

  // ── Helpers ──────────────────────────────────────────────────────────────

  function qs(sel, root = document) { return root.querySelector(sel); }
  function qsa(sel, root = document) { return [...root.querySelectorAll(sel)]; }

  function click(el) { if (el) el.click(); }

  function getPlayer() {
    return qs('video') || qs('#movie_player video');
  }

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
    // 1. Click skip button immediately
    for (const sel of AD_SKIP_SELECTORS) {
      const btn = qs(sel);
      if (btn) { click(btn); break; }
    }

    // 2. If unskippable ad: jump to end so it ends fast
    const adBadge = qs('.ytp-ad-simple-ad-badge, .ytp-ad-duration-remaining');
    if (adBadge) {
      const vid = getPlayer();
      if (vid && vid.duration && isFinite(vid.duration)) {
        vid.currentTime = vid.duration;
      }
    }

    // 3. Mute ad audio (better experience if ad plays briefly)
    const adPlaying = qs('.ad-showing');
    if (adPlaying) {
      const vid = getPlayer();
      if (vid) vid.muted = true;
    } else {
      const vid = getPlayer();
      if (vid && vid.muted && !userMuted) vid.muted = false;
    }

    // 4. Remove overlay ads
    for (const sel of AD_OVERLAY_SELECTORS) {
      qsa(sel).forEach(el => el.remove());
    }
  }

  // Track user mute state so we don't unmute manually muted videos
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
      /* Sidebar recommendations on watch page */
      #secondary { display: none !important; }
      /* Homepage feed noise */
      ytd-rich-shelf-renderer,
      ytd-shelf-renderer { display: none !important; }
      /* End screen cards overlay */
      .ytp-ce-element { display: none !important; }
      /* Info cards */
      .ytp-cards-teaser { display: none !important; }
      /* Merch shelf */
      ytd-merch-shelf-renderer { display: none !important; }
      /* Ticket shelf */
      ytd-ticket-shelf-renderer { display: none !important; }
      /* Memberships & clips row */
      ytd-channel-featured-content-renderer { display: none !important; }
      /* Smooth scroll everywhere */
      html { scroll-behavior: smooth !important; }
      /* Faster hover transitions */
      * { transition-duration: 0.1s !important; }
    `;
    document.head.appendChild(style);
  }

  // ── Shorts Redirect Blocker ──────────────────────────────────────────────
  function expandShortsToFull() {
    const url = location.href;
    if (url.includes('/shorts/')) {
      const id = url.split('/shorts/')[1].split('?')[0].split('/')[0];
      if (id) {
        location.replace(`https://www.youtube.com/watch?v=${id}`);
      }
    }
  }

  // ── Consent / Cookie Dialog Dismisser ───────────────────────────────────
  const CONSENT_TEXTS = [
    'Accetta tutto', 'Accept all', 'Accetta', 'Accept',
    'Agree', 'OK', 'Continua', 'Continue without',
  ];

  function dismissConsent() {
    // YouTube consent dialog
    const consentForms = qsa('form[action*="consent"]');
    consentForms.forEach(f => {
      const btn = [...f.querySelectorAll('button')].find(b =>
        CONSENT_TEXTS.some(t => b.textContent.trim().startsWith(t))
      );
      if (btn) click(btn);
    });

    // Generic overlay dialogs
    const dialogs = qsa('tp-yt-paper-dialog, ytd-consent-bump-v2-lightbox, .ytd-consent-bump-v2-lightbox');
    dialogs.forEach(d => {
      const btn = [...d.querySelectorAll('button, [role="button"]')].find(b =>
        CONSENT_TEXTS.some(t => b.textContent.trim().includes(t))
      );
      if (btn) click(btn);
    });
  }

  // ── Autoplay Countdown Skipper ───────────────────────────────────────────
  function skipCountdown() {
    const countdown = qs('.ytp-autonav-endscreen-upnext-countdown-overlay');
    if (countdown) {
      const nextBtn = qs('.ytp-autonav-endscreen-upnext-button');
      if (nextBtn) click(nextBtn);
    }
  }

  // ── Speed Control HUD ────────────────────────────────────────────────────
  function injectSpeedHUD() {
    if (qs('#fn-speed-hud')) return;
    const hud = document.createElement('div');
    hud.id = 'fn-speed-hud';
    hud.innerHTML = `
      <button id="fn-speed-down" title="Rallenta">−</button>
      <span id="fn-speed-label">1×</span>
      <button id="fn-speed-up" title="Accelera">+</button>
    `;
    document.body.appendChild(hud);

    const SPEEDS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.5, 3];
    let idx = SPEEDS.indexOf(cfg.defaultSpeed);
    if (idx === -1) idx = SPEEDS.indexOf(1);

    function applySpeed() {
      const vid = getPlayer();
      if (vid) vid.playbackRate = SPEEDS[idx];
      qs('#fn-speed-label').textContent = SPEEDS[idx] + '×';
    }

    qs('#fn-speed-up').addEventListener('click', (e) => {
      e.stopPropagation();
      if (idx < SPEEDS.length - 1) { idx++; applySpeed(); }
    });
    qs('#fn-speed-down').addEventListener('click', (e) => {
      e.stopPropagation();
      if (idx > 0) { idx--; applySpeed(); }
    });

    // Restore on video change
    document.addEventListener('yt-navigate-finish', () => {
      setTimeout(applySpeed, 800);
    });

    if (cfg.autoSpeed) applySpeed();
  }

  // ── Theater Mode ─────────────────────────────────────────────────────────
  function enableTheater() {
    const btn = qs('.ytp-size-button, button[data-tooltip-target-id="ytp-size-button"]');
    // Only activate if we're not already in theater/fullscreen
    if (btn && !document.body.classList.contains('ytd-watch-flexy[theater]')) {
      const isTheater = qs('ytd-watch-flexy[theater]');
      if (!isTheater) setTimeout(() => click(btn), 600);
    }
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

    // Overlay for gesture feedback
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

      // Tap detection (not a swipe)
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

      // Horizontal swipe → seek
      if (Math.abs(dx) > SWIPE_MIN && Math.abs(dx) > Math.abs(dy) * 1.5 && vid) {
        const seekAmt = Math.round((dx / playerArea.getBoundingClientRect().width) * 60);
        vid.currentTime = Math.max(0, Math.min(vid.duration || Infinity, vid.currentTime + seekAmt));
        showFeedback(seekAmt > 0 ? `⏩ +${seekAmt}s` : `⏪ ${seekAmt}s`);
        return;
      }

      // Vertical swipe on right half → volume
      if (Math.abs(dy) > SWIPE_MIN && Math.abs(dy) > Math.abs(dx) * 1.5 && vid) {
        const rect = playerArea.getBoundingClientRect();
        const rightHalf = touchStartX > rect.left + rect.width / 2;
        if (rightHalf) {
          const delta = -(dy / rect.height) * 0.5;
          vid.volume = Math.max(0, Math.min(1, vid.volume + delta));
          showFeedback(`🔊 ${Math.round(vid.volume * 100)}%`);
        } else {
          // Left half: brightness (CSS filter only)
          const bDelta = -(dy / rect.height) * 0.5;
          const currentBr = parseFloat(vid.style.filter?.match(/brightness\(([^)]+)\)/)?.[1] || 1);
          const newBr = Math.max(0.1, Math.min(2, currentBr + bDelta));
          vid.style.filter = `brightness(${newBr.toFixed(2)})`;
          showFeedback(`☀️ ${Math.round(newBr * 100)}%`);
        }
      }
    }, { passive: true });
  }

  // ── Auto-set default playback speed on new video ─────────────────────────
  function applyDefaultSpeed() {
    if (!cfg.autoSpeed) return;
    const vid = getPlayer();
    if (vid && cfg.defaultSpeed !== 1) {
      vid.playbackRate = cfg.defaultSpeed;
    }
  }

  // ── MutationObserver for dynamic content ────────────────────────────────
  function startObserver() {
    const obs = new MutationObserver(() => {
      if (cfg.skipAds) skipAd();
      if (cfg.autoDismissConsent) dismissConsent();
      if (cfg.skipCountdown) skipCountdown();
    });
    obs.observe(document.body, { childList: true, subtree: true });
  }

  // ── Navigation events (YouTube SPA) ─────────────────────────────────────
  function onNavigate() {
    if (cfg.hideShortsRedirect) expandShortsToFull();
    setTimeout(() => {
      if (cfg.autoTheater && isWatchPage()) enableTheater();
      applyDefaultSpeed();
      if (cfg.touchGestures) initTouchGestures();
    }, 1000);
  }

  function isWatchPage() {
    return location.pathname.startsWith('/watch');
  }

  // ── Keyboard shortcuts (useful even on tablet with keyboard) ─────────────
  function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;
      const vid = getPlayer();
      if (!vid) return;
      switch (e.key) {
        case 'ArrowRight': vid.currentTime += cfg.seekSeconds; break;
        case 'ArrowLeft':  vid.currentTime -= cfg.seekSeconds; break;
        case 'ArrowUp':    vid.volume = Math.min(1, vid.volume + 0.1); break;
        case 'ArrowDown':  vid.volume = Math.max(0, vid.volume - 0.1); break;
        case '>': vid.playbackRate = Math.min(3, vid.playbackRate + 0.25); break;
        case '<': vid.playbackRate = Math.max(0.25, vid.playbackRate - 0.25); break;
      }
    });
  }

  // ── Init ─────────────────────────────────────────────────────────────────
  function init() {
    if (cfg.hideShortsRedirect) expandShortsToFull();
    if (cfg.removeBloat) injectBloatStyle();
    if (cfg.autoDismissConsent) dismissConsent();
    if (cfg.skipAds) skipAd();

    startObserver();
    initKeyboardShortcuts();

    // Speed HUD always shown
    const hudCheck = setInterval(() => {
      if (document.body) {
        injectSpeedHUD();
        clearInterval(hudCheck);
      }
    }, 200);

    setTimeout(() => {
      if (cfg.touchGestures) initTouchGestures();
      if (cfg.autoTheater && isWatchPage()) enableTheater();
      applyDefaultSpeed();
    }, 1200);

    document.addEventListener('yt-navigate-finish', onNavigate);
    document.addEventListener('yt-page-data-updated', () => {
      if (cfg.skipAds) skipAd();
      applyDefaultSpeed();
    });
  }
})();
