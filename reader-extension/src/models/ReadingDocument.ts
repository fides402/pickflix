import type { SemanticUnit } from "./SemanticUnit";

export type ReadingDocumentSource = "demo" | "json" | "text-import" | "pdf-import";

export type ReadingDocument = {
  title: string;
  author?: string;
  units: SemanticUnit[];
  /**
   * A document imported from raw PDF/TXT without a ChatGPT-scored JSON has no
   * trustworthy semantic scores. `hasSemanticScores: false` marks it so the UI
   * can keep the reader in static mode until a matching scored JSON is imported.
   */
  hasSemanticScores: boolean;
  source: ReadingDocumentSource;
};
