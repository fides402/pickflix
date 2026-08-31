import type { AttentionState } from "../models/AttentionState";
import type { SemanticUnit } from "../models/SemanticUnit";
import { clamp01 } from "../models/SemanticUnit";

export type AttentionMode = "auto" | "manual";

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/**
 * MVP does not do real attention prediction. This produces a plausible,
 * organically-varying attention signal so the adaptive engine can be
 * exercised and demoed without eye tracking or interaction telemetry.
 *
 * Fatigue ramps slowly with time-on-task, engagement drifts toward what the
 * current unit's content suggests (emotion/intensity/narrativity keep it
 * up), and estimatedAttention combines both with a gentle organic
 * oscillation so it never feels like a straight line.
 */
export function simulateAttentionTick(
  state: AttentionState,
  elapsedMs: number,
  sessionMs: number,
  unit?: SemanticUnit,
): AttentionState {
  const fatigueGainPerMs = 0.000006;
  const fatigueRelief = unit ? unit.narrativity * 0.35 : 0;
  const fatigue = clamp01(state.fatigue + elapsedMs * fatigueGainPerMs * (1 - fatigueRelief * 0.5));

  const engagementTarget = unit
    ? clamp01(0.35 + unit.emotion * 0.3 + unit.intensity * 0.2 + unit.narrativity * 0.15)
    : state.engagement;
  const engagement = clamp01(lerp(state.engagement, engagementTarget, 0.12));

  const oscillation = Math.sin(sessionMs / 42000) * 0.05;
  const estimatedAttention = clamp01(
    engagement * (1 - fatigue * 0.55) + oscillation,
  );

  return { estimatedAttention, fatigue, engagement };
}

export function resetAttentionState(): AttentionState {
  return { estimatedAttention: 0.75, fatigue: 0.15, engagement: 0.7 };
}
