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
  (via `pdfjs-dist`) or TXT for a **static-mode** fallback (see below). A
  `RemoteAIProvider` (OpenAI or any other API) can be added later behind the
  same interface without touching the renderer.
- `src/store/` — Zustand store, persisted to `chrome.storage.local` (document,
  reading position, speed, adaptive on/off, theme/font/accessibility
  settings survive a reload).
- `src/components/` — Reader canvas/controls, the Debug panel, the two
  importers. No semantic logic lives here.

### PDF/TXT import vs. scored JSON import

This MVP intentionally does **not** run any AI inference inside the
extension. Uploading a PDF or TXT extracts the text locally and opens it in
**static mode** (uniform typography, `hasSemanticScores: false`) — the
"Adaptive ON/OFF" toggle is unavailable for these documents because there is
nothing genuine to adapt to. From that screen you can copy a ready-made
prompt ("Copia prompt per ChatGPT") that asks any LLM to score the same text
into this project's JSON schema; re-importing that JSON (via "Importa JSON
con punteggi") gives you the full adaptive experience, with the text and its
scores coming from the same place, as ChatGPT produces them together.

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
- **Carica PDF o TXT** — quick static-mode reading of your own file, plus the
  ChatGPT-prompt helper described above.
- **Adaptive ON/OFF** (top bar) — the A/B experiment: same content, adaptive
  engine on vs. a uniform static presentation.
- **Debug** (top bar) — current unit, all 8 content variables, attention/
  fatigue/engagement sliders (switches attention to manual mode), and every
  derived visual value, live.
- Keyboard: `Space` play/pause, `←`/`→` previous/next unit, `↑`/`↓` font
  size, `Escape` toggles the debug panel.

## What's deliberately not built (per spec)

Accounts, payments, a backend, EPUB/OCR parsing, ChatGPT UI scraping, real
AI inference inside the extension, eye tracking, cloud sync — all out of
scope for this MVP; the `ReadingScoreProvider` boundary is what a future
`RemoteAIProvider` would plug into.

## Notes

- `npm audit` flags a few moderate/high issues, all inside the `vite`/
  `esbuild`/`vitest` dev-tooling chain (the dev-server-only esbuild CORS
  advisory). They do not affect the built, shipped extension and are not
  fixed automatically to avoid a breaking Vite 8 upgrade during this MVP.
