/* Kiwi Fast Nav – Popup logic */

const FIELDS = [
  'skipAds', 'removeBloat', 'touchGestures', 'autoDismissConsent',
  'autoTheater', 'skipCountdown', 'hideShortsRedirect', 'seekSeconds',
];

const DEFAULT = {
  skipAds: true,
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
    if (node.type === 'checkbox') node.checked = !!cfg[key];
    else node.value = cfg[key];
  }
}

function collectUI() {
  const out = {};
  for (const key of FIELDS) {
    const node = el(key);
    if (!node) continue;
    if (node.type === 'checkbox') {
      out[key] = node.checked;
    } else {
      const v = parseFloat(node.value);
      out[key] = isNaN(v) ? node.value : v;
    }
  }
  return out;
}

chrome.storage.sync.get(DEFAULT, (cfg) => loadUI(cfg));

el('saveBtn').addEventListener('click', () => {
  const cfg = collectUI();
  chrome.storage.sync.set(cfg, () => {
    const status = el('save-status');
    status.textContent = '✓ Salvato';
    setTimeout(() => { status.textContent = ''; }, 2000);

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.url?.includes('youtube.com')) {
        chrome.tabs.reload(tabs[0].id);
      }
    });
  });
});
