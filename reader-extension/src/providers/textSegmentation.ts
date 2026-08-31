import type { SemanticUnit } from "../models/SemanticUnit";

const SENTENCE_SPLIT = /(?<=[.!?…])\s+(?=[A-ZÀ-Ý0-9"«“])/;
const MAX_UNIT_LENGTH = 220;

/**
 * Mechanical, non-semantic segmentation used only for raw PDF/TXT imports
 * that have no ChatGPT-produced score attached. Every unit gets identical,
 * neutral mid-range values so the reader stays in a calm, uniform "static"
 * presentation until the user imports a real scored JSON for this text.
 */
export function segmentPlainText(rawText: string, idPrefix: string): SemanticUnit[] {
  const paragraphs = rawText
    .replace(/\r\n/g, "\n")
    .split(/\n{2,}|\n(?=\s*\n)|\n/)
    .map((p) => p.trim())
    .filter(Boolean);

  const units: SemanticUnit[] = [];
  let counter = 0;

  for (const paragraph of paragraphs) {
    const sentences = paragraph.split(SENTENCE_SPLIT).map((s) => s.trim()).filter(Boolean);
    for (const sentence of sentences) {
      for (const chunk of splitLongSentence(sentence)) {
        counter += 1;
        units.push({
          id: `${idPrefix}-${counter}`,
          text: chunk,
          importance: 0.5,
          complexity: 0.4,
          intensity: 0.3,
          novelty: 0.4,
          emotion: 0.3,
          connectivity: 0.4,
          narrativity: 0.5,
          density: 0.4,
        });
      }
    }
  }

  return units;
}

function splitLongSentence(sentence: string): string[] {
  if (sentence.length <= MAX_UNIT_LENGTH) return [sentence];
  const parts = sentence.split(/,\s+/);
  const chunks: string[] = [];
  let current = "";
  for (const part of parts) {
    const candidate = current ? `${current}, ${part}` : part;
    if (candidate.length > MAX_UNIT_LENGTH && current) {
      chunks.push(current.trim());
      current = part;
    } else {
      current = candidate;
    }
  }
  if (current) chunks.push(current.trim());
  return chunks.length > 0 ? chunks : [sentence];
}
