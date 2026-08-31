export type ReadingRegime = "flow" | "focus" | "reveal" | "recovery" | "cruise";

export const READING_REGIMES: ReadingRegime[] = ["flow", "focus", "reveal", "recovery", "cruise"];

export const REGIME_LABELS: Record<ReadingRegime, string> = {
  flow: "Flow",
  focus: "Focus",
  reveal: "Reveal",
  recovery: "Recovery",
  cruise: "Cruise",
};
