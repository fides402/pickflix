import type { SemanticUnit } from "../models/SemanticUnit";
import type { AttentionState } from "../models/AttentionState";
import type { VisualState } from "../models/VisualState";
import type { ReadingRegime } from "../models/ReadingRegime";
import { deriveRegime } from "./regimeEngine";
import { deriveVisualState } from "./visualEngine";
import { deriveDuration } from "./durationEngine";

export type ReadingFrame = {
  regime: ReadingRegime;
  visual: VisualState;
  durationMs: number;
};

const STATIC_VISUAL: Omit<VisualState, "regime" | "layout"> = {
  fontSize: 1.55,
  fontWeight: 420,
  lineHeight: 1.6,
  maxWidth: 36,
  opacity: 1,
  contrast: 1,
  letterSpacing: 0,
  verticalPosition: 0,
  entranceDuration: 250,
  holdDuration: 600,
  exitDuration: 200,
  motionAmount: 0.1,
  contextVisibility: 0.5,
  surroundingWhitespace: 0.3,
  chunkScale: 1,
};

/**
 * Orchestrates the pure engine functions for a single semantic unit.
 * `adaptive: false` bypasses the semantic engine entirely and returns a
 * uniform visual state — this backs the "static vs adaptive" A/B toggle.
 */
export function computeReadingFrame(
  unit: SemanticUnit,
  attention: AttentionState,
  speedMultiplier: number,
  adaptive: boolean,
): ReadingFrame {
  if (!adaptive) {
    return {
      regime: "cruise",
      visual: { ...STATIC_VISUAL, regime: "cruise", layout: "center-focus" },
      durationMs: Math.round((unit.text.split(/\s+/).length * 260) / Math.max(0.1, speedMultiplier)),
    };
  }

  const regime = deriveRegime(unit, attention);
  const visual = deriveVisualState(unit, attention, regime);
  const durationMs = deriveDuration(unit, attention, speedMultiplier);

  return { regime, visual, durationMs };
}
