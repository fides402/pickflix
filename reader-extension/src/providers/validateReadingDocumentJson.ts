import type { ReadingDocument } from "../models/ReadingDocument";
import { SEMANTIC_SCALAR_KEYS } from "../models/SemanticUnit";

export type ValidationResult =
  | { ok: true; document: ReadingDocument }
  | { ok: false; errors: string[] };

/**
 * Validates the JSON import format described in the product spec:
 * { title, author?, units: [{ id, text, importance..density (0-1), ... }] }
 *
 * Collects readable, specific errors (up to a handful) instead of throwing,
 * so the UI can show the user exactly what to fix.
 */
export function validateReadingDocumentJson(raw: string): ValidationResult {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    return { ok: false, errors: [`Il file non è un JSON valido: ${(err as Error).message}`] };
  }

  const errors: string[] = [];

  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    return { ok: false, errors: ["Il JSON deve essere un oggetto con 'title' e 'units'."] };
  }

  const doc = parsed as Record<string, unknown>;

  if (typeof doc.title !== "string" || doc.title.trim().length === 0) {
    errors.push("Campo 'title' mancante o vuoto.");
  }
  if (doc.author !== undefined && typeof doc.author !== "string") {
    errors.push("Campo 'author' deve essere una stringa, se presente.");
  }

  if (!Array.isArray(doc.units) || doc.units.length === 0) {
    errors.push("Campo 'units' mancante o vuoto: serve almeno una semantic unit.");
    return { ok: false, errors };
  }

  const seenIds = new Set<string>();
  const units = doc.units as unknown[];
  units.forEach((rawUnit, index) => {
    if (typeof rawUnit !== "object" || rawUnit === null) {
      errors.push(`units[${index}] non è un oggetto.`);
      return;
    }
    const unit = rawUnit as Record<string, unknown>;
    const label = `units[${index}]${typeof unit.id === "string" ? ` (id="${unit.id}")` : ""}`;

    if (typeof unit.id !== "string" || unit.id.trim().length === 0) {
      errors.push(`${label}: campo 'id' mancante.`);
    } else if (seenIds.has(unit.id)) {
      errors.push(`${label}: id duplicato.`);
    } else {
      seenIds.add(unit.id);
    }

    if (typeof unit.text !== "string" || unit.text.trim().length === 0) {
      errors.push(`${label}: campo 'text' mancante o vuoto.`);
    }

    for (const key of SEMANTIC_SCALAR_KEYS) {
      const value = unit[key];
      if (typeof value !== "number" || Number.isNaN(value)) {
        errors.push(`${label}: campo '${key}' mancante o non numerico.`);
      } else if (value < 0 || value > 1) {
        errors.push(`${label}: campo '${key}' fuori range [0,1] (valore: ${value}).`);
      }
    }

    if (unit.suggestedDuration !== undefined) {
      if (typeof unit.suggestedDuration !== "number" || unit.suggestedDuration <= 0) {
        errors.push(`${label}: 'suggestedDuration' deve essere un numero positivo.`);
      }
    }
    if (unit.tags !== undefined) {
      if (!Array.isArray(unit.tags) || unit.tags.some((t) => typeof t !== "string")) {
        errors.push(`${label}: 'tags' deve essere un array di stringhe.`);
      }
    }
  });

  if (errors.length > 0) {
    return { ok: false, errors: errors.slice(0, 12) };
  }

  const document: ReadingDocument = {
    title: (doc.title as string).trim(),
    author: typeof doc.author === "string" ? doc.author.trim() : undefined,
    units: units as ReadingDocument["units"],
    hasSemanticScores: true,
    source: "json",
  };

  return { ok: true, document };
}
