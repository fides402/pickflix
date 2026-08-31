import { useState } from "react";
import { useReaderStore } from "../../store/readerStore";
import { REGIME_LABELS, type ReadingRegime } from "../../models/ReadingRegime";
import { SettingsPanel } from "./SettingsPanel";

type Props = {
  visible: boolean;
  regime: ReadingRegime | null;
  onHome: () => void;
};

export function TopBar({ visible, regime, onHome }: Props) {
  const document = useReaderStore((s) => s.document);
  const adaptiveRendering = useReaderStore((s) => s.adaptiveRendering);
  const setAdaptiveRendering = useReaderStore((s) => s.setAdaptiveRendering);
  const debugPanelOpen = useReaderStore((s) => s.debugPanelOpen);
  const toggleDebugPanel = useReaderStore((s) => s.toggleDebugPanel);
  const theme = useReaderStore((s) => s.settings.theme);
  const updateSettings = useReaderStore((s) => s.updateSettings);
  const liveSession = useReaderStore((s) => s.liveSession);
  const [settingsOpen, setSettingsOpen] = useState(false);

  if (!document) return null;

  return (
    <div className={`top-bar${visible ? "" : " hidden"}`}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.8rem" }}>
        <button className="icon-button" onClick={onHome} aria-label="Torna alla libreria" title="Libreria">
          ⌂
        </button>
        <div>
          <div className="top-bar-title">{document.title}</div>
          {regime && <div className="regime-badge">{REGIME_LABELS[regime]}</div>}
        </div>
      </div>

      <div className="top-bar-actions">
        {liveSession.active && (
          <span
            className="pill-toggle"
            title={liveSession.error ?? "Pipeline ChatGPT live"}
            style={liveSession.error ? { borderColor: "#c0392b", color: "#c0392b" } : undefined}
          >
            {liveSession.error
              ? "ChatGPT: errore ⚠"
              : liveSession.generating
                ? "Genero round successivo…"
                : liveSession.hasMore
                  ? `Round ${liveSession.roundsDone}/${liveSession.roundsTotal}+`
                  : "Tutti i round generati"}
          </span>
        )}

        <button
          className="pill-toggle"
          data-active={theme === "dark"}
          onClick={() => updateSettings({ theme: theme === "dark" ? "light" : "dark" })}
          title="Cambia tema chiaro/scuro"
        >
          {theme === "dark" ? "🌙 Scuro" : "☀︎ Chiaro"}
        </button>

        {document.hasSemanticScores && (
          <button
            className="pill-toggle"
            data-active={adaptiveRendering}
            onClick={() => setAdaptiveRendering(!adaptiveRendering)}
            title="Confronta lettura statica vs adattiva"
          >
            {adaptiveRendering ? "Adaptive ON" : "Adaptive OFF"}
          </button>
        )}

        <button
          className="pill-toggle"
          data-active={settingsOpen}
          onClick={() => setSettingsOpen((v) => !v)}
          title="Font e impostazioni di lettura"
        >
          Aa
        </button>

        <button
          className="pill-toggle"
          data-active={debugPanelOpen}
          onClick={toggleDebugPanel}
          title="Pannello di debug (dev)"
        >
          Debug
        </button>
      </div>

      {settingsOpen && <SettingsPanel onClose={() => setSettingsOpen(false)} />}
    </div>
  );
}
