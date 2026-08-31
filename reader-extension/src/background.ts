chrome.action.onClicked.addListener(() => {
  chrome.tabs.create({ url: chrome.runtime.getURL("reader.html") });
});

/**
 * Relays "generate a round" requests from reader.html to the chatgpt.com tab's
 * content script (chatgptBridge.ts). Message type string is duplicated here
 * (not imported) to keep chatgptBridge.ts import-free — see its header comment.
 */
const ROUND_REQUEST_TYPE = "ADAPTIVE_READER_ROUND_REQUEST";
const CONTENT_SCRIPT_MSG_TYPE = "ADAPTIVE_READER_GPT_SEND";
const CHATGPT_URL_PATTERNS = ["https://chatgpt.com/*", "https://chat.openai.com/*"];

let jobQueue: Promise<unknown> = Promise.resolve();

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function findOrCreateChatGptTab(): Promise<number> {
  const existing = await chrome.tabs.query({ url: CHATGPT_URL_PATTERNS });
  const withId = existing.find((t) => typeof t.id === "number");
  if (withId?.id) return withId.id;

  const created = await chrome.tabs.create({ url: "https://chatgpt.com/", active: false });
  if (!created.id) throw new Error("Impossibile aprire una scheda di chatgpt.com.");

  await new Promise<void>((resolve) => {
    function onUpdated(tabId: number, info: chrome.tabs.TabChangeInfo) {
      if (tabId === created.id && info.status === "complete") {
        chrome.tabs.onUpdated.removeListener(onUpdated);
        resolve();
      }
    }
    chrome.tabs.onUpdated.addListener(onUpdated);
  });
  await sleep(1500); // let the SPA hydrate and the content script attach
  return created.id;
}

async function sendToTabWithRetry(
  tabId: number,
  text: string,
  attempts = 4,
): Promise<{ ok: true; responseText: string } | { ok: false; error: string }> {
  for (let i = 0; i < attempts; i++) {
    try {
      const response = await chrome.tabs.sendMessage(tabId, { type: CONTENT_SCRIPT_MSG_TYPE, text });
      if (response) return response;
    } catch {
      // content script not ready yet, or tab navigated away — retry
    }
    await sleep(800);
  }
  return { ok: false, error: "Impossibile comunicare con la scheda di ChatGPT (content script non pronto)." };
}

async function handleRoundRequest(text: string) {
  const tabId = await findOrCreateChatGptTab();
  return sendToTabWithRetry(tabId, text);
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || message.type !== ROUND_REQUEST_TYPE) return undefined;
  jobQueue = jobQueue
    .then(() => handleRoundRequest(message.text as string))
    .catch((err) => ({ ok: false, error: err instanceof Error ? err.message : String(err) }));
  jobQueue.then(sendResponse);
  return true; // keep the message channel open for the async response
});
