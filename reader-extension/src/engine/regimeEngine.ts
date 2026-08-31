import type { SemanticUnit } from "../models/SemanticUnit";
import type { AttentionState } from "../models/AttentionState";
import type { ReadingRegime } from "../models/ReadingRegime";

/**
 * Reading regimes are not user-chosen modes: they emerge from a soft,
 * continuous score over the content variables and the attention state.
 * We compute a score per regime and pick the highest one, with a light
 * hard override for the extreme low-attention / high-fatigue case where
 * "recovery" should reliably win regardless of content.
 */
export function deriveRegime(unit: SemanticUnit, attention: AttentionState): ReadingRegime {
  if (attention.estimatedAttention < 0.22 || attention.fatigue > 0.85) {
    return "recovery";
  }

  const scores: Record<ReadingRegime, number> = {
    flow: unit.narrativity * 0.55 + (1 - unit.complexity) * 0.25 + attention.estimatedAttention * 0.2,
    focus: unit.importance * 0.5 + unit.complexity * 0.5,
    reveal: unit.novelty * 0.6 + unit.importance * 0.4,
    recovery:
      (1 - attention.estimatedAttention) * 0.4 + attention.fatigue * 0.35 + unit.density * 0.25,
    cruise:
      attention.estimatedAttention * 0.45 +
      (1 - unit.complexity) * 0.35 +
      (1 - Math.abs(unit.importance - 0.3)) * 0.2,
  };

  // Tie-break priority favours user wellbeing over content drama.
  const priority: ReadingRegime[] = ["recovery", "reveal", "focus", "flow", "cruise"];

  let best: ReadingRegime = "flow";
  let bestScore = -Infinity;
  for (const regime of priority) {
    const score = scores[regime];
    if (score > bestScore + 1e-9) {
      bestScore = score;
      best = regime;
    }
  }
  return best;
}
