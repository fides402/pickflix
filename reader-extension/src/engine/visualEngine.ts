import type { SemanticUnit } from "../models/SemanticUnit";
import type { AttentionState } from "../models/AttentionState";
import type { ReadingRegime } from "../models/ReadingRegime";
import type { ReaderLayout, VisualState } from "../models/VisualState";
import { clamp01 } from "../models/SemanticUnit";

function chooseLayout(unit: SemanticUnit, regime: ReadingRegime): ReaderLayout {
  if (regime === "reveal" && unit.novelty > 0.75) return "isolated-concept";
  if (regime === "flow" || regime === "cruise") return "flow-stack";
  return "center-focus";
}

/**
 * Turns Content State + Attention State into a Visual State.
 *
 * There is deliberately no `if (importance > 0.8) animation = "zoom"` style
 * branching here: every field is a continuous blend of the semantic
 * variables and the attention state. `regime` only nudges tone (which
 * layout, how fast transitions feel) — it never hard-switches a value.
 */
export function deriveVisualState(
  unit: SemanticUnit,
  attention: AttentionState,
  regime: ReadingRegime,
): VisualState {
  const calm = attention.estimatedAttention * (1 - attention.fatigue * 0.5);

  // importance ↑ -> larger, heavier, more contrast, more surrounding space
  const fontSize = 1.3 + unit.importance * 0.55 + unit.intensity * 0.15 - unit.density * 0.1;
  const fontWeight = 380 + unit.importance * 160 + (regime === "focus" ? 40 : 0);

  // complexity/density ↑ -> more line height, more breathing room
  const lineHeight = 1.4 + unit.complexity * 0.35 + unit.density * 0.2 - unit.narrativity * 0.08;

  // complexity/importance ↑ -> narrower column (isolation); narrativity ↑ -> wider, flowing column
  const maxWidth = 40 - unit.complexity * 9 - unit.importance * 4 + unit.narrativity * 6;

  const contrast = 0.92 + unit.importance * 0.14 + unit.intensity * 0.08;
  const opacity = 1;

  const letterSpacing = unit.complexity * 0.012 + (regime === "reveal" ? 0.01 : 0);

  const verticalPosition = clamp01(0.5 + (unit.complexity - unit.narrativity) * 0.15) * 2 - 1;

  // density/complexity ↑ -> slower entrance and longer hold; narrativity ↑ -> quicker, fluid transitions
  const entranceDuration =
    260 + unit.complexity * 260 + unit.importance * 140 - unit.narrativity * 90;
  const exitDuration = 200 + unit.complexity * 160 - unit.narrativity * 60;
  const holdDuration = 400 + unit.density * 500 + unit.importance * 300 - calm * 100;

  // intensity ↑ -> slightly more dynamic transitions; complexity/fatigue ↑ -> calmer, less motion
  const motionAmount = clamp01(
    0.18 + unit.intensity * 0.35 + unit.narrativity * 0.15 - unit.complexity * 0.2 - attention.fatigue * 0.15,
  );

  // narrativity ↑ -> more context kept on screen (sense of continuity/flow)
  // importance/novelty (reveal) ↑ -> context recedes so the new unit stands out
  const contextVisibility = clamp01(
    0.45 + unit.narrativity * 0.3 - unit.importance * 0.2 - unit.novelty * 0.15 + calm * 0.1,
  );

  // importance/complexity/density ↑ -> more whitespace around the unit
  const surroundingWhitespace = clamp01(
    0.25 + unit.importance * 0.3 + unit.complexity * 0.25 + unit.density * 0.2 - unit.narrativity * 0.1,
  );

  // importance/intensity ↑ -> slightly larger presence; recovery calms it back down
  const chunkScale = 1 + unit.importance * 0.12 + unit.intensity * 0.08 - (regime === "recovery" ? 0.06 : 0);

  return {
    regime,
    layout: chooseLayout(unit, regime),
    fontSize: round2(fontSize),
    fontWeight: Math.round(clampRange(fontWeight, 380, 640)),
    lineHeight: round2(lineHeight),
    maxWidth: round2(clampRange(maxWidth, 22, 46)),
    opacity,
    contrast: round2(clampRange(contrast, 0.85, 1.18)),
    letterSpacing: round3(letterSpacing),
    verticalPosition: round2(clampRange(verticalPosition, -0.3, 0.3)),
    entranceDuration: Math.round(clampRange(entranceDuration, 180, 700)),
    holdDuration: Math.round(clampRange(holdDuration, 300, 1400)),
    exitDuration: Math.round(clampRange(exitDuration, 150, 500)),
    motionAmount: round2(motionAmount),
    contextVisibility: round2(contextVisibility),
    surroundingWhitespace: round2(surroundingWhitespace),
    chunkScale: round2(clampRange(chunkScale, 0.85, 1.35)),
  };
}

function clampRange(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
function round2(v: number): number {
  return Math.round(v * 100) / 100;
}
function round3(v: number): number {
  return Math.round(v * 1000) / 1000;
}
