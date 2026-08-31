import { describe, expect, it } from "vitest";
import { deriveVisualState } from "./visualEngine";
import type { SemanticUnit } from "../models/SemanticUnit";
import type { AttentionState } from "../models/AttentionState";

function unit(overrides: Partial<SemanticUnit> = {}): SemanticUnit {
  return {
    id: "u",
    text: "testo di prova",
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

describe("deriveVisualState", () => {
  it("grows font size and whitespace as importance increases", () => {
    const low = deriveVisualState(unit({ importance: 0.1 }), baseAttention, "focus");
    const high = deriveVisualState(unit({ importance: 0.95 }), baseAttention, "focus");
    expect(high.fontSize).toBeGreaterThan(low.fontSize);
    expect(high.surroundingWhitespace).toBeGreaterThan(low.surroundingWhitespace);
  });

  it("narrows the column and reduces motion as complexity increases", () => {
    const low = deriveVisualState(unit({ complexity: 0.05 }), baseAttention, "focus");
    const high = deriveVisualState(unit({ complexity: 0.95 }), baseAttention, "focus");
    expect(high.maxWidth).toBeLessThan(low.maxWidth);
    expect(high.motionAmount).toBeLessThan(low.motionAmount);
  });

  it("increases context visibility as narrativity increases", () => {
    const low = deriveVisualState(unit({ narrativity: 0.05 }), baseAttention, "flow");
    const high = deriveVisualState(unit({ narrativity: 0.95 }), baseAttention, "flow");
    expect(high.contextVisibility).toBeGreaterThan(low.contextVisibility);
  });

  it("reduces context visibility for a high-novelty reveal moment", () => {
    const low = deriveVisualState(unit({ novelty: 0.05, importance: 0.3 }), baseAttention, "reveal");
    const high = deriveVisualState(unit({ novelty: 0.95, importance: 0.9 }), baseAttention, "reveal");
    expect(high.contextVisibility).toBeLessThan(low.contextVisibility);
  });

  it("chooses isolated-concept layout for a strong reveal moment", () => {
    const visual = deriveVisualState(unit({ novelty: 0.9 }), baseAttention, "reveal");
    expect(visual.layout).toBe("isolated-concept");
  });

  it("chooses flow-stack layout for flow and cruise regimes", () => {
    expect(deriveVisualState(unit(), baseAttention, "flow").layout).toBe("flow-stack");
    expect(deriveVisualState(unit(), baseAttention, "cruise").layout).toBe("flow-stack");
  });

  it("keeps every numeric field finite and within sane bounds for all-zero content", () => {
    const visual = deriveVisualState(
      unit({ importance: 0, complexity: 0, intensity: 0, novelty: 0, emotion: 0, connectivity: 0, narrativity: 0, density: 0 }),
      { estimatedAttention: 0, fatigue: 0, engagement: 0 },
      "recovery",
    );
    for (const [key, value] of Object.entries(visual)) {
      if (typeof value === "number") {
        expect(Number.isFinite(value), `${key} should be finite`).toBe(true);
      }
    }
    expect(visual.fontSize).toBeGreaterThan(0);
    expect(visual.lineHeight).toBeGreaterThan(0);
  });

  it("keeps every numeric field finite and within sane bounds for all-one content", () => {
    const visual = deriveVisualState(
      unit({ importance: 1, complexity: 1, intensity: 1, novelty: 1, emotion: 1, connectivity: 1, narrativity: 1, density: 1 }),
      { estimatedAttention: 1, fatigue: 1, engagement: 1 },
      "focus",
    );
    for (const [key, value] of Object.entries(visual)) {
      if (typeof value === "number") {
        expect(Number.isFinite(value), `${key} should be finite`).toBe(true);
      }
    }
    expect(visual.fontWeight).toBeLessThanOrEqual(640);
    expect(visual.maxWidth).toBeGreaterThanOrEqual(22);
  });
});
