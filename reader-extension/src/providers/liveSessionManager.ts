import { ChatGptLiveSession } from "./ChatGptLiveSession";

/**
 * Module-level singleton: the ChatGptLiveSession instance needs to outlive
 * the component that started it (the landing screen's FileImporter) and be
 * reachable from the reader canvas (useLiveRoundPrefetch), which are never
 * mounted at the same time. The store only mirrors its status for the UI.
 */
let session: ChatGptLiveSession | null = null;

export function startLiveSession(sourceText: string, title: string): ChatGptLiveSession {
  session = new ChatGptLiveSession(sourceText, title);
  return session;
}

export function getLiveSession(): ChatGptLiveSession | null {
  return session;
}

export function clearLiveSession(): void {
  session = null;
}
