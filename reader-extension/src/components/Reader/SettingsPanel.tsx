import { useReaderStore } from "../../store/readerStore";
import { FONT_OPTIONS } from "../../styles/fonts";

export function SettingsPanel({ onClose }: { onClose: () => void }) {
  const settings = useReaderStore((s) => s.settings);
  const updateSettings = useReaderStore((s) => s.updateSettings);

  return (
    <div
      className="debug-panel"
      style={{ width: "min(18rem, 90vw)" }}
      onClick={(e) => e.stopPropagation()}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.6rem" }}>
        <h2>Impostazioni</h2>
        <button className="icon-button" style={{ width: "2rem", height: "2rem" }} onClick={onClose} aria-label="Chiudi">
          ×
        </button>
      </div>

      <div className="debug-section">
        <h3>Font di lettura</h3>
        {FONT_OPTIONS.map((f) => (
          <label key={f.id} className="settings-row" style={{ cursor: "pointer" }}>
            <span style={{ fontFamily: f.cssFamily }}>{f.label}</span>
            <input
              type="radio"
              name="fontFamily"
              checked={settings.fontFamily === f.id}
              onChange={() => updateSettings({ fontFamily: f.id })}
            />
          </label>
        ))}
      </div>

      <div className="debug-section">
        <h3>Tipografia</h3>
        <div className="settings-row">
          <span>Dimensione testo</span>
          <div>
            <button className="icon-button" style={{ width: "1.9rem", height: "1.9rem" }} onClick={() => updateSettings({ fontScale: Math.max(0.75, settings.fontScale - 0.06) })}>
              −
            </button>
            <button className="icon-button" style={{ width: "1.9rem", height: "1.9rem", marginLeft: "0.3rem" }} onClick={() => updateSettings({ fontScale: Math.min(1.6, settings.fontScale + 0.06) })}>
              +
            </button>
          </div>
        </div>
        <div className="settings-row">
          <span>Interlinea</span>
          <div>
            <button className="icon-button" style={{ width: "1.9rem", height: "1.9rem" }} onClick={() => updateSettings({ lineHeightScale: Math.max(0.85, settings.lineHeightScale - 0.05) })}>
              −
            </button>
            <button className="icon-button" style={{ width: "1.9rem", height: "1.9rem", marginLeft: "0.3rem" }} onClick={() => updateSettings({ lineHeightScale: Math.min(1.3, settings.lineHeightScale + 0.05) })}>
              +
            </button>
          </div>
        </div>
      </div>

      <div className="debug-section">
        <h3>Accessibilità</h3>
        <label className="settings-row" style={{ cursor: "pointer" }}>
          <span>Riduci le animazioni</span>
          <input
            type="checkbox"
            checked={settings.reducedMotion}
            onChange={(e) => updateSettings({ reducedMotion: e.target.checked })}
          />
        </label>
      </div>
    </div>
  );
}
