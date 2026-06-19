// Content script — ChatGPT interaction + auto-sync to chrome.storage

let msgCountBeforeSend = 0;
let responseText       = '';
let responseTextAt     = 0;
let sendTime           = 0;
let monitorTimer       = null;

// ── On inject: restore persisted state so a tab reload doesn't break polling ──
chrome.storage.local.get(['_sendTime', '_msgCountBeforeSend'], data => {
  if (data._sendTime) {
    sendTime           = data._sendTime;
    msgCountBeforeSend = data._msgCountBeforeSend || 0;
    // Resume writing state to storage so the popup can keep reading
    startStorageMonitor();
  }
});

// ── Router ──
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'uploadPdfAndPrompt') {
    handleUploadAndPrompt(msg.pdfBase64, msg.pdfName, msg.prompt)
      .then(() => sendResponse({ success: true }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }
  if (msg.action === 'sendPrompt') {
    handleSendPrompt(msg.prompt)
      .then(() => sendResponse({ success: true }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }
  // Legacy direct-poll fallback (still supported)
  if (msg.action === 'getLatestResponse') {
    sendResponse(buildResponseState());
    return true;
  }
});

// ── Upload PDF then send prompt ──
async function handleUploadAndPrompt(pdfBase64, pdfName, prompt) {
  const byteChars = atob(pdfBase64);
  const bytes = new Uint8Array(byteChars.length);
  for (let i = 0; i < byteChars.length; i++) bytes[i] = byteChars.charCodeAt(i);
  const file = new File([bytes], pdfName, { type: 'application/pdf' });

  const fileInput = await waitFor(
    () => document.querySelector('#upload-files') || document.querySelector('input[type="file"]'),
    10000, 'file input non trovato'
  );

  const dt = new DataTransfer();
  dt.items.add(file);
  fileInput.files = dt.files;
  fileInput.dispatchEvent(new Event('change', { bubbles: true }));

  await waitFor(
    () => !!document.querySelector('[data-testid="send-button"]'),
    60000, 'il pulsante invio non è comparso dopo il caricamento del file'
  );

  const composerRoot =
    fileInput.closest('form') ||
    document.querySelector('form') ||
    document.querySelector('[data-testid="composer"]') ||
    document.body;

  await waitForDomToSettle(composerRoot, 2000);
  await sleep(500);
  await handleSendPrompt(prompt);
}

// ── Send text prompt ──
async function handleSendPrompt(prompt) {
  // Reset in-memory state
  msgCountBeforeSend = countMessages();
  responseText       = '';
  responseTextAt     = 0;
  sendTime           = 0;

  // Persist initial state so popup can immediately show "sending"
  await storeState({ done: false, text: '', generating: false, textLength: 0, newMsgAppeared: false });

  const input = await waitFor(getPromptInput, 8000, 'campo testo ChatGPT non trovato');
  input.focus();
  await sleep(200);

  if (input.tagName === 'TEXTAREA') {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
    setter.call(input, prompt);
    input.dispatchEvent(new Event('input', { bubbles: true }));
  } else {
    input.innerHTML = '';
    document.execCommand('insertText', false, prompt);
    if (!input.textContent.trim()) {
      input.textContent = prompt;
      input.dispatchEvent(new InputEvent('input', { bubbles: true }));
    }
  }

  await waitFor(getSendButton, 6000, 'pulsante invio non abilitato');
  await sleep(200);

  getSendButton().click();
  sendTime = Date.now();

  // Persist send metadata so a tab reload can restore monitoring
  chrome.storage.local.set({ _sendTime: sendTime, _msgCountBeforeSend: msgCountBeforeSend });

  startStorageMonitor();
}

// ── Auto-monitor: writes response state to storage every 1.2s ──
function startStorageMonitor() {
  if (monitorTimer) clearInterval(monitorTimer);
  monitorTimer = setInterval(() => {
    const state = buildResponseState();
    storeState(state);
    if (state.done) {
      clearInterval(monitorTimer);
      monitorTimer = null;
      // Clean up send metadata — no longer needed
      chrome.storage.local.remove(['_sendTime', '_msgCountBeforeSend']);
    }
  }, 1200);
}

// ── Build current response state ──
function buildResponseState() {
  const generating = isGenerating();
  const text       = getNewAssistantText();

  if (text !== responseText) {
    responseText   = text;
    responseTextAt = Date.now();
  }

  const now            = Date.now();
  const stable         = responseTextAt > 0 && (now - responseTextAt) > 5000;
  const waited         = sendTime > 0 && (now - sendTime) > 8000;
  const newMsgAppeared = countMessages() > msgCountBeforeSend;
  const done           = !generating && stable && waited && newMsgAppeared && text.length > 100;

  return { done, text, generating, textLength: text.length, newMsgAppeared };
}

function storeState(state) {
  return new Promise(resolve => chrome.storage.local.set({ _responseState: state }, resolve));
}

// ── DOM helpers ──
function countMessages() {
  return document.querySelectorAll('[data-message-author-role]').length;
}

function isGenerating() {
  return !!(
    document.querySelector('[data-testid="stop-button"]') ||
    document.querySelector('button[aria-label="Stop generating"]') ||
    document.querySelector('button[aria-label="Interrompi generazione"]') ||
    document.querySelector('button[aria-label="Stop streaming"]')
  );
}

function getNewAssistantText() {
  const msgs = document.querySelectorAll('[data-message-author-role="assistant"]');
  if (!msgs.length) return '';
  const last = msgs[msgs.length - 1];
  return (last.innerText || last.textContent || '').trim();
}

function getPromptInput() {
  return (
    document.querySelector('#prompt-textarea') ||
    document.querySelector('textarea[data-id="root"]') ||
    document.querySelector('[contenteditable="true"][data-testid="text-input"]') ||
    document.querySelector('div[contenteditable="true"].ProseMirror') ||
    document.querySelector('[contenteditable="true"]')
  );
}

function getSendButton() {
  const candidates = [
    document.querySelector('[data-testid="send-button"]'),
    document.querySelector('button[aria-label="Send message"]'),
    document.querySelector('button[aria-label="Invia messaggio"]'),
    ...Array.from(document.querySelectorAll('button[type="submit"]')),
  ];
  return candidates.find(b => b && !b.disabled) || null;
}

function waitFor(fn, timeout = 10000, label = '') {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const iv = setInterval(() => {
      const r = fn();
      if (r) { clearInterval(iv); resolve(r); }
      else if (Date.now() - start > timeout) {
        clearInterval(iv);
        reject(new Error(`Timeout (${Math.round(timeout / 1000)}s)${label ? ': ' + label : ''}`));
      }
    }, 500);
  });
}

function waitForDomToSettle(target, settleMs = 2000) {
  return new Promise(resolve => {
    let timer = null;
    const bump = () => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => { observer.disconnect(); resolve(); }, settleMs);
    };
    const observer = new MutationObserver(bump);
    observer.observe(target, { childList: true, subtree: true, attributes: true, characterData: true });
    bump();
  });
}

const sleep = ms => new Promise(r => setTimeout(r, ms));
