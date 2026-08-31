# Adaptive Immersive Reader

Chrome extension (Manifest V3) MVP: a book/text becomes a fullscreen, immersive
reading experience where the typography — chunk size, pacing, whitespace,
motion — reacts continuously to the *meaning* of the text and to a (simulated)
attention state. The content never changes, only how it's presented.

## Architecture

```
Content (PDF/TXT/JSON) → Semantic Units (+ scores 0-1) → reading engine
  (regimeEngine → visualEngine + durationEngine) → React renderer
```

- `src/engine/` — pure, unit-tested functions. No React, no DOM. `deriveRegime`
  picks one of five emergent regimes (Flow, Focus, Reveal, Recovery, Cruise)
  from the content scores + attention state. `deriveVisualState` turns those
  into a continuous `VisualState` (font size, line height, motion amount,
  context visibility, ...) — there is no `if (importance > 0.8) zoom` style
  branching, every value is a blend. `deriveDuration` computes on-screen time.
- `src/providers/` — the `ReadingScoreProvider` boundary. `DemoProvider` ships
  a built-in story; `LocalJsonProvider`/`validateReadingDocumentJson` handle
  the scored-JSON import format; `fileImport.ts` extracts raw text from PDF
  (via `pdfjs-dist`) or TXT for a **static-mode** fallback (see below).
  `ChatGptLiveSession` drives the live ChatGPT pipeline (see next section).
- `src/store/` — Zustand store, persisted to `chrome.storage.local` (document,
  reading position, speed, adaptive on/off, theme/font/accessibility
  settings survive a reload).
- `src/components/` — Reader canvas/controls, the Debug panel, the two
  importers. No semantic logic lives here.

### PDF/TXT import: three ways to get scores

Uploading a PDF or TXT only ever extracts text locally — the extension does
not run any AI model itself. From the "«file» pronto" card you get three
options:

1. **Genera con ChatGPT (beta)** — the live pipeline described below.
2. **Copia prompt per ChatGPT** — copies a ready-made prompt into your
   clipboard; paste it into ChatGPT (web, app, whatever), get back JSON, then
   import it via "Importa JSON con punteggi". Manual, but robust — no
   automation, so it never breaks.
3. **Apri lettura statica** — read the raw text immediately, no scores,
   uniform typography (`hasSemanticScores: false`, the "Adaptive ON/OFF"
   toggle stays hidden since there's nothing genuine to adapt to).

#### The live ChatGPT pipeline (experimental)

"Genera con ChatGPT" automates the **consumer chatgpt.com web app** (not the
OpenAI API): it opens (or reuses) a `chatgpt.com` tab, pastes a chunk of your
text into the composer, submits it, and scrapes the assistant's reply out of
the page's DOM — exactly what you'd do by hand, just automated. It uses
whatever ChatGPT session is already logged into that browser profile.

- **Round-ahead prefetch, as requested**: the source text is split into
  ~3200-character rounds (`ChatGptLiveSession`, `CHARS_PER_ROUND`). Round 1 is
  generated before the reader opens. From then on, `useLiveRoundPrefetch`
  watches your reading position and — once you're within 5 units of the end
  of what's currently loaded — silently requests the next round in the
  background, so it's ready by the time you get there. A pill in the top bar
  ("Genero round successivo…" / "Round N/M+") shows what's happening.
- **Read this before relying on it**: automating the ChatGPT web UI is
  **unofficial and outside OpenAI's supported integration surface** — it can
  violate ChatGPT's Terms of Service, and it **will** break the moment OpenAI
  changes the composer/send-button/message DOM structure. Everything
  DOM-specific lives in one file, `src/contentScripts/chatgptBridge.ts`
  (selectors at the top — `COMPOSER_SELECTORS`, `SEND_BUTTON_SELECTORS`,
  `STOP_BUTTON_SELECTORS`, `ASSISTANT_MESSAGE_SELECTOR`), specifically so it's
  the only place to patch when it breaks. **This could not be end-to-end
  tested against the live chatgpt.com site in the environment this was built
  in** (no network route to chatgpt.com there) — only the surrounding
  plumbing (permissions, tab creation/reuse, message relay, retries, timeout,
  and the error-surfacing UI) was verified. If a round fails, the error shows
  in the importer with a pointer back to the manual "Copia prompt" fallback.
- **New permissions this adds**: `tabs`, `scripting`, and host access to
  `https://chatgpt.com/*` and `https://chat.openai.com/*` (declared in
  `public/manifest.json`), plus a content script injected into those pages.
  Chrome grants these automatically for a developer-mode unpacked load; a
  Web Store listing would show them to the user as a permission request.
- How a round is requested: `reader.html` (`ChatGptLiveSession`) →
  `chrome.runtime.sendMessage` → `background.ts` (finds/creates the
  chatgpt.com tab, serializes requests through a small queue) →
  `chrome.tabs.sendMessage` → `chatgptBridge.ts` in that tab (types the
  prompt, clicks send, polls for the reply to stop streaming, returns the
  raw text) → back up the chain → `ChatGptLiveSession` parses/validates the
  JSON (reusing `validateReadingDocumentJson`) into `SemanticUnit[]`.

## Fonts

Three free, self-hosted (no CDN, bundled via `@fontsource`, MV3-CSP-safe)
serif families tuned for long-form reading — Literata (default), Source
Serif 4, Lora — switchable from the "Aa" settings panel, plus Inter for the
UI chrome.

## Setup

```bash
npm install
npm run build     # tsc --noEmit && vite build → dist/
npm test          # vitest: regimeEngine, visualEngine, durationEngine, JSON validation
npm run dev        # Vite dev server (for iterating on components in isolation)
```

## Load unpacked in Chrome

1. `npm run build` (produces `dist/`)
2. Open `chrome://extensions`
3. Enable "Developer mode" (top right)
4. Click "Load unpacked" and select the `reader-extension/dist` folder
5. Click the extension's toolbar icon — it opens `reader.html` in a new tab

## Using it

- **Prova la demo** — a short original story (56 semantic units) with all
  five reading regimes represented.
- **Importa JSON con punteggi** — the real adaptive path; see the format in
  `src/data/demoBook.ts` / the prompt copied from a PDF/TXT import.
- **Carica PDF o TXT** — extracts your file's text, then choose live ChatGPT
  generation, the manual prompt-copy fallback, or static reading (see above).
- **Adaptive ON/OFF** (top bar) — the A/B experiment: same content, adaptive
  engine on vs. a uniform static presentation.
- **Debug** (top bar) — current unit, all 8 content variables, attention/
  fatigue/engagement sliders (switches attention to manual mode), and every
  derived visual value, live.
- Keyboard: `Space` play/pause, `←`/`→` previous/next unit, `↑`/`↓` font
  size, `Escape` toggles the debug panel.

## What's deliberately not built (per spec)

Accounts, payments, a backend, EPUB/OCR parsing, a real OpenAI-API-based
provider, eye tracking, cloud sync — all out of scope for this MVP. (The
ChatGPT web-UI automation above *was* explicitly requested and built despite
the original spec's "avoid AI integration" guidance — see the risk callout.)

## Notes

- `npm audit` flags a few moderate/high issues, all inside the `vite`/
  `esbuild`/`vitest` dev-tooling chain (the dev-server-only esbuild CORS
  advisory). They do not affect the built, shipped extension and are not
  fixed automatically to avoid a breaking Vite 8 upgrade during this MVP.
