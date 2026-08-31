import { useRef, useState } from "react";
import { importFile, FileImportError } from "../../providers/fileImport";
import { buildChatGptPrompt } from "../../providers/chatGptPromptTemplate";
import { useReaderStore } from "../../store/readerStore";
import type { ReadingDocument } from "../../models/ReadingDocument";

export function FileImporter() {
  const inputRef = useRef<HTMLInputElement>(null);
  const loadDocument = useReaderStore((s) => s.loadDocument);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<ReadingDocument | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError(null);
    setCopied(false);
    setLoading(true);
    try {
      const doc = await importFile(file);
      setPending(doc);
    } catch (err) {
      setError(err instanceof FileImportError ? err.message : `Import fallito: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  }

  async function copyPrompt() {
    if (!pending) return;
    const fullText = pending.units.map((u) => u.text).join(" ");
    const prompt = buildChatGptPrompt(fullText, pending.title);
    await navigator.clipboard.writeText(prompt);
    setCopied(true);
  }

  return (
    <>
      <label className="action-card" onClick={() => inputRef.current?.click()}>
        <h3>Carica PDF o TXT</h3>
        <p>
          Estrae il testo direttamente nell'estensione e apre subito una lettura in modalità statica (uniforme).
          Per la lettura adattiva, genera poi il JSON con punteggi via ChatGPT e reimportalo.
        </p>
        <input ref={inputRef} type="file" accept=".pdf,.txt,application/pdf,text/plain" onChange={handleChange} />
      </label>

      {loading && <div className="import-error" style={{ background: "transparent", color: "var(--text-secondary)", border: "none" }}>Estrazione del testo in corso…</div>}
      {error && <div className="import-error">{error}</div>}

      {pending && (
        <div className="action-card" style={{ cursor: "default" }}>
          <h3>«{pending.title}» pronto</h3>
          <p>
            {pending.units.length} unità estratte, senza punteggi semantici. Puoi leggerlo subito in modalità
            statica, oppure copiare un prompt pronto per ChatGPT che genera il JSON con i punteggi da reimportare.
          </p>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.6rem", flexWrap: "wrap" }}>
            <button
              className="icon-button"
              style={{ width: "auto", padding: "0 0.9rem", borderRadius: "999px" }}
              onClick={(evt) => {
                evt.stopPropagation();
                loadDocument(pending);
              }}
            >
              Apri lettura statica
            </button>
            <button
              className="icon-button"
              style={{ width: "auto", padding: "0 0.9rem", borderRadius: "999px" }}
              onClick={(evt) => {
                evt.stopPropagation();
                copyPrompt();
              }}
            >
              {copied ? "Prompt copiato ✓" : "Copia prompt per ChatGPT"}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
