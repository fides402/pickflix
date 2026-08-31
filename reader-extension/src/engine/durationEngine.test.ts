import { describe, expect, it } from "vitest";
import { deriveDuration } from "./durationEngine";
import type { SemanticUnit } from "../models/SemanticUnit";
import type { AttentionState } from "../models/AttentionState";

function unit(overrides: Partial<SemanticUnit> = {}): SemanticUnit {
  return {
    id: "u",
    text: "una frase di media lunghezza per il test",
    importance: 0.5,
    complexity: 0.5,
    intensity: 0.5,
    novelty: 0.5,
    emotion: 0.5,
    connectivity: 0.5,
    narrativity: 0.5,
    density: 0.5,
    ...overrides,
  };
}

const baseAttention: AttentionState = { estimatedAttention: 0.7, fatigue: 0.2, engagement: 0.7 };

describe("deriveDuration", () => {
  it("returns a positive duration for a normal unit", () => {
    expect(deriveDuration(unit(), baseAttention)).toBeGreaterThan(0);
  });

  it("increases duration as complexity increases, all else equal", () => {
    const low = deriveDuration(unit({ complexity: 0.1 }), baseAttention);
    const high = deriveDuration(unit({ complexity: 0.9 }), baseAttention);
    expect(high).toBeGreaterThan(low);
  });

  it("increases duration as density increases, all else equal", () => {
    const low = deriveDuration(unit({ density: 0.1 }), baseAttention);
    const high = deriveDuration(unit({ density: 0.9 }), baseAttention);
    expect(high).toBeGreaterThan(low);
  });

  it("increases duration when attention is very low", () => {
    const focused = deriveDuration(unit(), { estimatedAttention: 0.9, fatigue: 0.05, engagement: 0.9 });
    const distracted = deriveDuration(unit(), { estimatedAttention: 0.05, fatigue: 0.2, engagement: 0.5 });
    expect(distracted).toBeGreaterThan(focused);
  });

  it("increases duration when fatigue is very high", () => {
    const rested = deriveDuration(unit(), { estimatedAttention: 0.7, fatigue: 0.05, engagement: 0.7 });
    const exhausted = deriveDuration(unit(), { estimatedAttention: 0.7, fatigue: 0.95, engagement: 0.7 });
    expect(exhausted).toBeGreaterThan(rested);
  });

  it("scales down with a higher speed multiplier", () => {
    const normal = deriveDuration(unit(), baseAttention, 1);
    const fast = deriveDuration(unit(), baseAttention, 2);
    expect(fast).toBeLessThan(normal);
  });

  it("respects an explicit suggestedDuration override", () => {
    const duration = deriveDuration(unit({ suggestedDuration: 5000 }), baseAttention, 1);
    expect(duration).toBe(5000);
  });

  it("never returns a duration below the minimum floor for a one-word unit", () => {
    const duration = deriveDuration(unit({ text: "Ciao." }), baseAttention);
    expect(duration).toBeGreaterThanOrEqual(700);
  });

  it("stays within the maximum ceiling for a very long, dense, complex unit", () => {
    const longText = Array.from({ length: 400 }, () => "parola").join(" ");
    const duration = deriveDuration(
      unit({ text: longText, complexity: 1, importance: 1, density: 1 }),
      { estimatedAttention: 0, fatigue: 1, engagement: 0 },
      0.4,
    );
    expect(duration).toBeLessThanOrEqual(22000);
  });

  it("handles all-zero content variables without throwing", () => {
    const duration = deriveDuration(
      unit({ importance: 0, complexity: 0, intensity: 0, novelty: 0, emotion: 0, connectivity: 0, narrativity: 0, density: 0 }),
      { estimatedAttention: 0, fatigue: 0, engagement: 0 },
    );
    expect(Number.isFinite(duration)).toBe(true);
    expect(duration).toBeGreaterThan(0);
  });
});
