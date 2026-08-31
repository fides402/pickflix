import type { ReadingScoreProvider } from "./ReadingScoreProvider";
import type { ReadingDocument } from "../models/ReadingDocument";
import { validateReadingDocumentJson } from "./validateReadingDocumentJson";

export class LocalJsonProvider implements ReadingScoreProvider {
  async getReadingScore(rawJson: string): Promise<ReadingDocument> {
    const result = validateReadingDocumentJson(rawJson);
    if (!result.ok) {
      throw new Error(result.errors.join("\n"));
    }
    return result.document;
  }
}
