import type { ReadingDocument } from "../models/ReadingDocument";

/**
 * Boundary between "content intelligence" (whatever analyzes a book and
 * produces a semantic reading score) and the extension. Today only
 * DemoProvider and LocalJsonProvider exist. A future RemoteAIProvider
 * (OpenAI API, a proprietary backend, ...) can implement this same
 * interface without the reader/renderer code changing at all.
 */
export interface ReadingScoreProvider {
  getReadingScore(input: string): Promise<ReadingDocument>;
}
