import { describe, expect, it } from "vitest";
import { deriveRegime } from "./regimeEngine";
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

function attention(overrides: Partial<AttentionState> = {}): AttentionState {
  return { estimatedAttention: 0.7, fatigue: 0.2, engagement: 0.7, ...overrides };
}

describe("deriveRegime", () => {
  it("picks focus for high importance + high complexity", () => {
    const regime = deriveRegime(unit({ importance: 0.9, complexity: 0.9, novelty: 0.2 }), attention());
    expect(regime).toBe("focus");
  });

  it("picks reveal for high novelty + high importance, higher than focus", () => {
    const regime = deriveRegime(
      unit({ importance: 0.85, novelty: 0.95, complexity: 0.2 }),
      attention(),
    );
    expect(regime).toBe("reveal");
  });

  it("picks flow for high narrativity + low complexity + decent attention", () => {
    const regime = deriveRegime(
      unit({ narrativity: 0.95, complexity: 0.1, importance: 0.3, novelty: 0.2 }),
      attention({ estimatedAttention: 0.8 }),
    );
    expect(regime).toBe("flow");
  });

  it("picks cruise for high attention + low complexity + medium-low importance", () => {
    const regime = deriveRegime(
      unit({ complexity: 0.05, importance: 0.3, narrativity: 0.3, novelty: 0.1 }),
      attention({ estimatedAttention: 0.95, fatigue: 0.05 }),
    );
    expect(regime).toBe("cruise");
  });

  it("forces recovery when attention is extremely low, regardless of content", () => {
    const regime = deriveRegime(unit({ importance: 0.9, novelty: 0.9 }), attention({ estimatedAttention: 0.05 }));
    expect(regime).toBe("recovery");
  });

  it("forces recovery when fatigue is extremely high, regardless of content", () => {
    const regime = deriveRegime(unit({ narrativity: 0.9 }), attention({ fatigue: 0.95 }));
    expect(regime).toBe("recovery");
  });

  it("handles all-zero content variables without throwing", () => {
    const regime = deriveRegime(
      unit({
        importance: 0,
        complexity: 0,
        intensity: 0,
        novelty: 0,
        emotion: 0,
        connectivity: 0,
        narrativity: 0,
        density: 0,
      }),
      attention(),
    );
    expect(["flow", "focus", "reveal", "recovery", "cruise"]).toContain(regime);
  });

  it("handles all-one content variables without throwing", () => {
    const regime = deriveRegime(
      unit({
        importance: 1,
        complexity: 1,
        intensity: 1,
        novelty: 1,
        emotion: 1,
        connectivity: 1,
        narrativity: 1,
        density: 1,
      }),
      attention(),
    );
    expect(["flow", "focus", "reveal", "recovery", "cruise"]).toContain(regime);
  });

  it("is deterministic for identical inputs", () => {
    const u = unit({ importance: 0.4, complexity: 0.6 });
    const a = attention();
    expect(deriveRegime(u, a)).toBe(deriveRegime(u, a));
  });
});
