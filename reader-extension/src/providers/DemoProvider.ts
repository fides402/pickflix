import type { ReadingScoreProvider } from "./ReadingScoreProvider";
import type { ReadingDocument } from "../models/ReadingDocument";
import { demoBook } from "../data/demoBook";

export class DemoProvider implements ReadingScoreProvider {
  async getReadingScore(_input: string): Promise<ReadingDocument> {
    return demoBook;
  }
}
