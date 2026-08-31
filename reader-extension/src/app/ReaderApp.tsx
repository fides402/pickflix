import { useEffect, useRef, useState } from "react";
import { useReaderStore } from "../store/readerStore";
import { DemoProvider } from "../providers/DemoProvider";
import { ReaderCanvas } from "../components/Reader/ReaderCanvas";
import { JsonImporter } from "../components/Import/JsonImporter";
import { FileImporter } from "../components/Import/FileImporter";
import { DebugPanel } from "../components/Debug/DebugPanel";

const demoProvider = new DemoProvider();

export function ReaderApp() {
  const activeDocument = useReaderStore((s) => s.document);
  const loadDocument = useReaderStore((s) => s.loadDocument);
  const theme = useReaderStore((s) => s.settings.theme);
  const debugPanelOpen = useReaderStore((s) => s.debugPanelOpen);
  const [showLibrary, setShowLibrary] = useState(!activeDocument);

  useEffect(() => {
    const root = window.document.documentElement;
    if (theme === "system") {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", theme);
    }
  }, [theme]);

  // Any newly loaded document (demo, JSON import, file import) should leave
  // the library screen automatically. A same-reference restore on mount
  // (persisted state) or an intentional "Home" click must not trigger this.
  const lastDocumentRef = useRef(activeDocument);
  useEffect(() => {
    if (activeDocument && activeDocument !== lastDocumentRef.current) {
      setShowLibrary(false);
    }
    lastDocumentRef.current = activeDocument;
  }, [activeDocument]);

  async function openDemo() {
    const doc = await demoProvider.getReadingScore("");
    loadDocument(doc);
  }

  if (!activeDocument || showLibrary) {
    return (
      <div className="app-shell">
        <div className="landing">
          <h1>Adaptive Immersive Reader</h1>
          <p className="subtitle">
            La stessa parola, presentata in modo diverso a seconda di cosa significa. Scegli come iniziare: prova la
            demo, importa un JSON già scorato da ChatGPT, oppure carica direttamente un PDF o un TXT.
          </p>
          <div className="landing-actions">
            <button
              className="action-card"
              style={{
                cursor: "pointer",
                border: "1px solid var(--border)",
                background: "var(--bg-elevated)",
                textAlign: "left",
              }}
              onClick={openDemo}
            >
              <h3>Prova la demo</h3>
              <p>Un breve racconto originale con tutti e cinque i regimi di lettura già pronti da esplorare.</p>
            </button>
            <JsonImporter />
            <FileImporter />
          </div>
          {activeDocument && (
            <button
              className="pill-toggle"
              onClick={() => setShowLibrary(false)}
              style={{ marginTop: "0.5rem" }}
            >
              ← Torna a «{activeDocument.title}»
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <>
      <ReaderCanvas onHome={() => setShowLibrary(true)} />
      {debugPanelOpen && <DebugPanel />}
    </>
  );
}
