export {};

/**
 * Content script injected into chatgpt.com / chat.openai.com. Automates the
 * consumer ChatGPT web UI: pastes a prompt into the composer, sends it,
 * waits for the reply to finish streaming, and returns the assistant's raw
 * text to the background script.
 *
 * This is inherently fragile (unofficial, DOM-selector based, breaks on any
 * ChatGPT redesign) and outside OpenAI's supported integration surface —
 * kept isolated in this single file so it's the only place to patch when it
 * breaks. Message type strings below are duplicated (not imported) in
 * background.ts on purpose: this file must stay import-free so it bundles
 * as a plain classic content script.
 */

const MSG_TYPE = "ADAPTIVE_READER_GPT_SEND";

const COMPOSER_SELECTORS = [
  "#prompt-textarea",
  'div[contenteditable="true"][data-testid="prompt-textarea"]',
  'textarea[data-testid="prompt-textarea"]',
  'div[contenteditable="true"]',
];

const SEND_BUTTON_SELECTORS = [
  '[data-testid="send-button"]',
  'button[aria-label*="Send" i]',
  'button[aria-label*="Invia" i]',
];

const STOP_BUTTON_SELECTORS = [
  '[data-testid="stop-button"]',
  'button[aria-label*="Stop" i]',
  'button[aria-label*="Interrompi" i]',
  'button[aria-label*="Ferma" i]',
];

const ASSISTANT_MESSAGE_SELECTOR = '[data-message-author-role="assistant"]';

const RESPONSE_TIMEOUT_MS = 150000;
// Fast path: the stop/streaming button was seen and has now disappeared — a
// reliable positive "done" signal, so a short stability window is enough.
const STABLE_WINDOW_WITH_SIGNAL_MS = 1500;
// Slow, conservative path: we never managed to detect the stop button at all
// (selector mismatch, different locale, redesign, ...). Text merely looking
// unchanged between two 400ms polls is NOT enough evidence it's finished —
// require a much longer, uninterrupted stable window before trusting it.
const STABLE_WINDOW_NO_SIGNAL_MS = 4500;
const POLL_INTERVAL_MS = 400;

function queryFirst(selectors: string[]): Element | null {
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el) return el;
  }
  return null;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function setComposerText(el: Element, text: string): void {
  const target = el as HTMLElement;
  target.focus();

  const selection = window.getSelection();
  if (selection) {
    const range = document.createRange();
    range.selectNodeContents(target);
    selection.removeAllRanges();
    selection.addRange(range);
  }

  let inserted = false;
  try {
    inserted = document.execCommand("insertText", false, text);
  } catch {
    inserted = false;
  }

  if (!inserted) {
    target.textContent = text;
    target.dispatchEvent(new InputEvent("input", { bubbles: true, cancelable: true, data: text, inputType: "insertText" }));
  }
}

async function sendPrompt(text: string): Promise<void> {
  const composer = queryFirst(COMPOSER_SELECTORS);
  if (!composer) throw new Error("Composer di ChatGPT non trovato: l'interfaccia potrebbe essere cambiata.");

  setComposerText(composer, text);
  await sleep(300);

  const sendButton = queryFirst(SEND_BUTTON_SELECTORS) as HTMLButtonElement | null;
  if (sendButton && !sendButton.disabled) {
    sendButton.click();
    return;
  }

  composer.dispatchEvent(
    new KeyboardEvent("keydown", { bubbles: true, cancelable: true, key: "Enter", code: "Enter" }),
  );
}

async function waitForReply(): Promise<string> {
  const startedAt = Date.now();
  let lastText = "";
  let stableSince = 0;
  let everSawStopButton = false;

  while (Date.now() - startedAt < RESPONSE_TIMEOUT_MS) {
    await sleep(POLL_INTERVAL_MS);

    const stopButtonPresent = !!queryFirst(STOP_BUTTON_SELECTORS);
    if (stopButtonPresent) everSawStopButton = true;

    const messages = document.querySelectorAll(ASSISTANT_MESSAGE_SELECTOR);
    const last = messages[messages.length - 1];
    const currentText = last ? (last as HTMLElement).innerText.trim() : "";

    if (currentText && currentText === lastText) {
      if (stableSince === 0) stableSince = Date.now();
    } else {
      stableSince = 0;
    }
    lastText = currentText;
    if (!currentText || stableSince === 0) continue;

    const stableMs = Date.now() - stableSince;

    if (everSawStopButton) {
      // We have a reliable signal: only trust stability once the stop
      // button has actually gone away (never while it's still showing,
      // no matter how "stable" the text looks mid-stream).
      if (!stopButtonPresent && stableMs >= STABLE_WINDOW_WITH_SIGNAL_MS) return currentText;
    } else if (stableMs >= STABLE_WINDOW_NO_SIGNAL_MS) {
      return currentText;
    }
  }

  throw new Error("Timeout: ChatGPT non ha risposto in tempo (l'interfaccia potrebbe essere cambiata o la risposta è troppo lunga).");
}

async function handleSend(text: string): Promise<{ ok: true; responseText: string } | { ok: false; error: string }> {
  try {
    await sendPrompt(text);
    const responseText = await waitForReply();
    return { ok: true, responseText };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || message.type !== MSG_TYPE) return undefined;
  handleSend(message.text as string).then(sendResponse);
  return true; // keep the message channel open for the async response
});
