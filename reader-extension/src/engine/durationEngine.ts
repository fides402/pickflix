import type { SemanticUnit } from "../models/SemanticUnit";
import type { AttentionState } from "../models/AttentionState";

const MS_PER_WORD_AT_BASE_PACE = 260; // ~230 wpm baseline
const MIN_DURATION_MS = 700;
const MAX_DURATION_MS = 22000;

function baseReadingTime(text: string): number {
  const words = text.trim().split(/\s+/).filter(Boolean).length || 1;
  return words * MS_PER_WORD_AT_BASE_PACE;
}

/**
 * duration = baseReadingTime(text)
 *          * complexityModifier
 *          * importanceModifier
 *          * densityModifier
 *          * attentionModifier
 *          / speedMultiplier
 *
 * Kept as an isolated, pure module so it can be unit tested and tuned
 * independently from rendering.
 */
export function deriveDuration(
  unit: SemanticUnit,
  attention: AttentionState,
  speedMultiplier: number = 1,
): number {
  if (unit.suggestedDuration && unit.suggestedDuration > 0) {
    return clamp(unit.suggestedDuration / Math.max(0.1, speedMultiplier));
  }

  const base = baseReadingTime(unit.text);

  const complexityModifier = 1 + unit.complexity * 0.8;
  const importanceModifier = 1 + unit.importance * 0.4;
  const densityModifier = 1 + unit.density * 0.5;
  const attentionModifier =
    1 +
    (1 - attention.estimatedAttention) * 0.5 +
    attention.fatigue * 0.3 -
    attention.engagement * 0.1;

  const duration =
    (base * complexityModifier * importanceModifier * densityModifier * attentionModifier) /
    Math.max(0.1, speedMultiplier);

  return clamp(duration);
}

function clamp(ms: number): number {
  return Math.min(MAX_DURATION_MS, Math.max(MIN_DURATION_MS, Math.round(ms)));
}
