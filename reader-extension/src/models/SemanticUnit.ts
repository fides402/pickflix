export type SemanticUnit = {
  id: string;
  text: string;

  /** 0 -> 1, how important the content is to understand/remember */
  importance: number;
  /** 0 -> 1, how much cognitive effort it requires */
  complexity: number;
  /** 0 -> 1, how dramatic/significant the moment feels */
  intensity: number;
  /** 0 -> 1, how much new information is being introduced */
  novelty: number;
  /** 0 -> 1, emotional charge of the content */
  emotion: number;
  /** 0 -> 1, how much it depends on / links to prior concepts */
  connectivity: number;
  /** 0 (abstract/expository) -> 1 (action/narrative/dialogue/event) */
  narrativity: number;
  /** 0 -> 1, information transmitted per unit of text */
  density: number;

  /** optional explicit override, in milliseconds */
  suggestedDuration?: number;

  tags?: string[];
};

export const SEMANTIC_SCALAR_KEYS = [
  "importance",
  "complexity",
  "intensity",
  "novelty",
  "emotion",
  "connectivity",
  "narrativity",
  "density",
] as const;

export type SemanticScalarKey = (typeof SEMANTIC_SCALAR_KEYS)[number];

export function clamp01(value: number): number {
  if (Number.isNaN(value)) return 0;
  return Math.min(1, Math.max(0, value));
}
