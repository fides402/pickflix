import { useRef, useState } from "react";
import { validateReadingDocumentJson } from "../../providers/validateReadingDocumentJson";
import { useReaderStore } from "../../store/readerStore";

export function JsonImporter() {
  const inputRef = useRef<HTMLInputElement>(null);
  const loadDocument = useReaderStore((s) => s.loadDocument);
  const [errors, setErrors] = useState<string[] | null>(null);

  async function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setErrors(null);
    try {
      const raw = await file.text();
      const result = validateReadingDocumentJson(raw);
      if (!result.ok) {
        setErrors(result.errors);
        return;
      }
      loadDocument(result.document);
    } catch (err) {
      setErrors([(err as Error).message]);
    }
  }

  return (
    <>
      <label className="action-card" onClick={() => inputRef.current?.click()}>
        <h3>Importa JSON con punteggi</h3>
        <p>
          Carica il JSON generato da ChatGPT (o compilato a mano) con testo e punteggi semantici già insieme:
          è la via per la lettura davvero adattiva.
        </p>
        <input ref={inputRef} type="file" accept="application/json,.json" onChange={handleChange} />
      </label>
      {errors && (
        <div className="import-error">
          Import JSON non riuscito:
          {"\n"}
          {errors.map((e) => `• ${e}`).join("\n")}
        </div>
      )}
    </>
  );
}
