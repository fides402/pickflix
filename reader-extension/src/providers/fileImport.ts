import type { ReadingDocument } from "../models/ReadingDocument";
import { segmentPlainText } from "./textSegmentation";

export class FileImportError extends Error {}

export async function importTextFile(file: File): Promise<ReadingDocument> {
  const text = await file.text();
  if (!text.trim()) {
    throw new FileImportError("Il file di testo è vuoto.");
  }
  return {
    title: stripExtension(file.name),
    units: segmentPlainText(text, "txt"),
    hasSemanticScores: false,
    source: "text-import",
  };
}

export async function importPdfFile(file: File): Promise<ReadingDocument> {
  const pdfjsLib = await import("pdfjs-dist");
  const workerUrl = (await import("pdfjs-dist/build/pdf.worker.min.mjs?url")).default;
  pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

  const buffer = await file.arrayBuffer();
  const loadingTask = pdfjsLib.getDocument({ data: buffer });
  const pdf = await loadingTask.promise;

  const pageTexts: string[] = [];
  for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
    const page = await pdf.getPage(pageNumber);
    const content = await page.getTextContent();
    const pageText = content.items
      .map((item) => ("str" in item ? item.str : ""))
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();
    if (pageText) pageTexts.push(pageText);
  }

  const fullText = pageTexts.join("\n\n");
  if (!fullText.trim()) {
    throw new FileImportError(
      "Non è stato possibile estrarre testo da questo PDF (potrebbe essere una scansione senza OCR).",
    );
  }

  return {
    title: stripExtension(file.name),
    units: segmentPlainText(fullText, "pdf"),
    hasSemanticScores: false,
    source: "pdf-import",
  };
}

export async function importFile(file: File): Promise<ReadingDocument> {
  const name = file.name.toLowerCase();
  if (name.endsWith(".pdf") || file.type === "application/pdf") {
    return importPdfFile(file);
  }
  if (name.endsWith(".txt") || file.type === "text/plain") {
    return importTextFile(file);
  }
  throw new FileImportError("Formato non supportato: carica un file .pdf o .txt.");
}

function stripExtension(filename: string): string {
  return filename.replace(/\.[^.]+$/, "");
}
