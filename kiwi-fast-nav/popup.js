/* Kiwi Fast Nav – Popup logic */

const FIELDS = [
  'skipAds', 'autoSpeed', 'defaultSpeed', 'removeBloat',
  'touchGestures', 'autoDismissConsent', 'autoTheater',
  'skipCountdown', 'hideShortsRedirect', 'seekSeconds',
];

const DEFAULT = {
  skipAds: true,
  autoSpeed: false,
  defaultSpeed: 1,
  removeBloat: true,
  touchGestures: true,
  autoDismissConsent: true,
  autoTheater: false,
  skipCountdown: true,
  hideShortsRedirect: true,
  seekSeconds: 10,
};

function el(id) { return document.getElementById(id); }

function loadUI(cfg) {
  for (const key of FIELDS) {
    const node = el(key);
    if (!node) continue;
    if (node.type === 'checkbox') {
      node.checked = !!cfg[key];
    } else {
      node.value = cfg[key];
    }
  }
  toggleSpeedRow(cfg.autoSpeed);
}

function collectUI() {
  const out = {};
  for (const key of FIELDS) {
    const node = el(key);
    if (!node) continue;
    if (node.type === 'checkbox') {
      out[key] = node.checked;
    } else if (node.tagName === 'SELECT') {
      const v = parseFloat(node.value);
      out[key] = isNaN(v) ? node.value : v;
    } else {
      out[key] = node.value;
    }
  }
  return out;
}

function toggleSpeedRow(enabled) {
  const row = el('speedRow');
  if (row) row.style.opacity = enabled ? '1' : '0.4';
  const sel = el('defaultSpeed');
  if (sel) sel.disabled = !enabled;
}

// Load saved settings
chrome.storage.sync.get(DEFAULT, (cfg) => loadUI(cfg));

// Live toggle of speed sub-row
el('autoSpeed').addEventListener('change', (e) => toggleSpeedRow(e.target.checked));

// Save
el('saveBtn').addEventListener('click', () => {
  const cfg = collectUI();
  chrome.storage.sync.set(cfg, () => {
    const status = el('save-status');
    status.textContent = '✓ Salvato';
    setTimeout(() => { status.textContent = ''; }, 2000);

    // Reload active YouTube tab to apply changes
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.url?.includes('youtube.com')) {
        chrome.tabs.reload(tabs[0].id);
      }
    });
  });
});
