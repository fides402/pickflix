import { useRef, useState } from "react";
import { importFile, FileImportError, type FileImportResult } from "../../providers/fileImport";
import { buildChatGptPrompt } from "../../providers/chatGptPromptTemplate";
import { startLiveSession } from "../../providers/liveSessionManager";
import { useReaderStore } from "../../store/readerStore";

export function FileImporter() {
  const inputRef = useRef<HTMLInputElement>(null);
  const loadDocument = useReaderStore((s) => s.loadDocument);
  const setLiveSessionStatus = useReaderStore((s) => s.setLiveSessionStatus);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<FileImportResult | null>(null);
  const [copied, setCopied] = useState(false);
  const [startingLive, setStartingLive] = useState(false);

  async function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError(null);
    setCopied(false);
    setLoading(true);
    try {
      const result = await importFile(file);
      setPending(result);
    } catch (err) {
      setError(err instanceof FileImportError ? err.message : `Import fallito: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  }

  async function copyPrompt() {
    if (!pending) return;
    const prompt = buildChatGptPrompt(pending.rawText, pending.document.title);
    await navigator.clipboard.writeText(prompt);
    setCopied(true);
  }

  async function startLive() {
    if (!pending) return;
    setError(null);
    setStartingLive(true);
    try {
      const session = startLiveSession(pending.rawText, pending.document.title);
      const firstRoundUnits = await session.requestNextRound();
      loadDocument({
        title: pending.document.title,
        units: firstRoundUnits,
        hasSemanticScores: true,
        source: pending.document.source,
      });
      const progress = session.progress;
      setLiveSessionStatus({
        active: true,
        generating: false,
        hasMore: session.hasMoreRounds,
        error: null,
        roundsDone: progress.doneRounds,
        roundsTotal: progress.totalRounds,
      });
    } catch (err) {
      setError(
        `Generazione con ChatGPT non riuscita: ${err instanceof Error ? err.message : String(err)}\n` +
          "Assicurati di essere loggato su chatgpt.com in questo browser, oppure usa 'Copia prompt per ChatGPT' come alternativa manuale.",
      );
    } finally {
      setStartingLive(false);
    }
  }

  return (
    <>
      <label className="action-card" onClick={() => inputRef.current?.click()}>
        <h3>Carica PDF o TXT</h3>
        <p>
          Estrae il testo direttamente nell'estensione. Da qui puoi generare i punteggi in automatico con ChatGPT,
          copiare un prompt manuale, oppure leggere subito in modalità statica.
        </p>
        <input ref={inputRef} type="file" accept=".pdf,.txt,application/pdf,text/plain" onChange={handleChange} />
      </label>

      {loading && <div className="import-error" style={{ background: "transparent", color: "var(--text-secondary)", border: "none" }}>Estrazione del testo in corso…</div>}
      {error && <div className="import-error">{error}</div>}

      {pending && (
        <div className="action-card" style={{ cursor: "default" }}>
          <h3>«{pending.document.title}» pronto</h3>
          <p>
            {pending.document.units.length} unità estratte, senza punteggi semantici. "Genera con ChatGPT" apre (o
            riusa) una scheda di chatgpt.com, incolla il testo a piccole porzioni e prepara automaticamente il round
            successivo mentre leggi quello attuale.
          </p>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.6rem", flexWrap: "wrap" }}>
            <button
              className="icon-button"
              style={{
                width: "auto",
                padding: "0 0.9rem",
                borderRadius: "999px",
                background: "var(--accent)",
                color: "#fff",
                borderColor: "var(--accent)",
              }}
              disabled={startingLive}
              onClick={(evt) => {
                evt.stopPropagation();
                startLive();
              }}
            >
              {startingLive ? "Generazione round 1…" : "Genera con ChatGPT (beta)"}
            </button>
            <button
              className="icon-button"
              style={{ width: "auto", padding: "0 0.9rem", borderRadius: "999px" }}
              onClick={(evt) => {
                evt.stopPropagation();
                loadDocument(pending.document);
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
