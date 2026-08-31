import { validateReadingDocumentJson } from "./validateReadingDocumentJson";
import type { SemanticUnit } from "../models/SemanticUnit";

// Must match background.ts's ROUND_REQUEST_TYPE exactly.
const ROUND_REQUEST_TYPE = "ADAPTIVE_READER_ROUND_REQUEST";

const CHARS_PER_ROUND = 3200;

type BackgroundResponse = { ok: true; responseText: string } | { ok: false; error: string };

/**
 * Drives the "live" ChatGPT pipeline: splits a source text into rounds,
 * sends one round at a time to the chatgpt.com tab (via background.ts +
 * chatgptBridge.ts), and returns validated SemanticUnits per round. The
 * caller (useLiveRoundPrefetch) decides *when* to call requestNextRound —
 * this class only knows how to produce one round on demand.
 */
export class ChatGptLiveSession {
  private chunks: string[];
  private nextIndex = 0;
  private roundCount = 0;

  constructor(
    sourceText: string,
    private title: string,
  ) {
    this.chunks = chunkText(sourceText, CHARS_PER_ROUND);
  }

  get hasMoreRounds(): boolean {
    return this.nextIndex < this.chunks.length;
  }

  get progress(): { doneRounds: number; totalRounds: number } {
    return { doneRounds: this.roundCount, totalRounds: this.chunks.length };
  }

  async requestNextRound(): Promise<SemanticUnit[]> {
    if (!this.hasMoreRounds) return [];

    const chunk = this.chunks[this.nextIndex];
    const roundNumber = this.nextIndex + 1;
    const prompt = buildRoundPrompt(chunk, roundNumber === 1);

    const response = (await chrome.runtime.sendMessage({
      type: ROUND_REQUEST_TYPE,
      text: prompt,
    })) as BackgroundResponse | undefined;

    if (!response || response.ok !== true) {
      throw new Error(response?.ok === false ? response.error : "Nessuna risposta da ChatGPT.");
    }

    const parsed = extractJson(response.responseText);
    const units = extractUnitsArray(parsed);
    if (!units) {
      throw new Error(
        `La risposta di ChatGPT non contiene un campo 'units' valido. Anteprima della risposta ricevuta:\n"${preview(response.responseText)}"`,
      );
    }

    const namespacedUnits = units.map((unit) => {
      if (unit && typeof unit === "object" && "id" in unit) {
        const record = unit as Record<string, unknown>;
        return { ...record, id: `r${roundNumber}-${record.id}` };
      }
      return unit;
    });

    const validation = validateReadingDocumentJson(
      JSON.stringify({ title: this.title, units: namespacedUnits }),
    );
    if (!validation.ok) {
      throw new Error(`Round ${roundNumber} non valido:\n${validation.errors.join("\n")}`);
    }

    this.nextIndex += 1;
    this.roundCount += 1;
    return validation.document.units;
  }
}

function chunkText(text: string, targetChars: number): string[] {
  const paragraphs = text
    .replace(/\r\n/g, "\n")
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);

  const chunks: string[] = [];
  let current = "";
  for (const paragraph of paragraphs) {
    const candidate = current ? `${current}\n\n${paragraph}` : paragraph;
    if (candidate.length > targetChars && current) {
      chunks.push(current);
      current = paragraph;
    } else {
      current = candidate;
    }
  }
  if (current) chunks.push(current);
  return chunks.length > 0 ? chunks : [text];
}

function buildRoundPrompt(chunk: string, isFirstRound: boolean): string {
  const intro = isFirstRound
    ? 'Sei un analista editoriale. Da ora in poi ti invierò il testo di un libro a piccole porzioni, una alla volta. Per OGNI porzione che ricevi, in questa stessa conversazione:'
    : "Ecco la porzione successiva dello stesso testo. Applica esattamente lo stesso schema di prima:";

  return `${intro}
Suddividila in "semantic units" (frasi brevi o mezze frasi, ognuna un'unità di lettura coerente) e per ciascuna assegna 8 punteggi normalizzati tra 0 e 1:
- importance: quanto è importante da capire/ricordare
- complexity: quanto richiede elaborazione cognitiva
- intensity: quanto il momento è forte/drammatico
- novelty: quanto introduce qualcosa di nuovo
- emotion: carica emotiva
- connectivity: quanto dipende da/collega concetti precedenti
- narrativity: 0 = spiegazione astratta, 1 = azione/narrazione/dialogo
- density: quanta informazione per unità di testo

Rispondi SOLO con un JSON valido, senza testo prima o dopo, senza blocchi markdown, in questo formato esatto:
{"units":[{"id":"1","text":"porzione di testo originale, invariata","importance":0.0,"complexity":0.0,"intensity":0.0,"novelty":0.0,"emotion":0.0,"connectivity":0.0,"narrativity":0.0,"density":0.0}]}

Non aggiungere, riassumere o tradurre il testo: ogni "text" deve essere una porzione letterale del testo qui sotto, e l'unione di tutte le unità deve ricostruire l'intera porzione, nell'ordine originale.

Testo da analizzare:
"""
${chunk}
"""`;
}

function extractJson(raw: string): unknown {
  const stripped = raw
    .trim()
    .replace(/^```(json)?/i, "")
    .replace(/```$/, "")
    .trim();
  try {
    return JSON.parse(stripped);
  } catch {
    const start = stripped.indexOf("{");
    const end = stripped.lastIndexOf("}");
    if (start >= 0 && end > start) {
      try {
        return JSON.parse(stripped.slice(start, end + 1));
      } catch {
        return null;
      }
    }
    return null;
  }
}

function extractUnitsArray(parsed: unknown): unknown[] | null {
  if (parsed && typeof parsed === "object" && Array.isArray((parsed as { units?: unknown }).units)) {
    return (parsed as { units: unknown[] }).units;
  }
  return null;
}

function preview(text: string, maxLength = 300): string {
  const trimmed = text.trim();
  return trimmed.length > maxLength ? `${trimmed.slice(0, maxLength)}…` : trimmed;
}
