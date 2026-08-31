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

const STOP_BUTTON_SELECTORS = ['[data-testid="stop-button"]', 'button[aria-label*="Stop" i]'];

const ASSISTANT_MESSAGE_SELECTOR = '[data-message-author-role="assistant"]';

const RESPONSE_TIMEOUT_MS = 150000;
const STABILITY_WINDOW_MS = 1400;
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
  let sawStreamingStart = false;

  while (Date.now() - startedAt < RESPONSE_TIMEOUT_MS) {
    await sleep(POLL_INTERVAL_MS);

    const stopButton = queryFirst(STOP_BUTTON_SELECTORS);
    if (stopButton) sawStreamingStart = true;

    const messages = document.querySelectorAll(ASSISTANT_MESSAGE_SELECTOR);
    const last = messages[messages.length - 1];
    const currentText = last ? (last as HTMLElement).innerText.trim() : "";

    if (currentText && currentText === lastText) {
      if (stableSince === 0) stableSince = Date.now();
      const stableLongEnough = Date.now() - stableSince >= STABILITY_WINDOW_MS;
      const streamingFinished = sawStreamingStart ? !stopButton : Date.now() - startedAt > 3000;
      if (stableLongEnough && streamingFinished) {
        return currentText;
      }
    } else {
      stableSince = 0;
    }
    lastText = currentText;
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
