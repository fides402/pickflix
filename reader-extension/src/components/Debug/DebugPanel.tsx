import { useReaderStore } from "../../store/readerStore";
import { useReadingEngine } from "../../hooks/useReadingEngine";
import { VariableSlider } from "./VariableSlider";
import { SEMANTIC_SCALAR_KEYS } from "../../models/SemanticUnit";
import { REGIME_LABELS } from "../../models/ReadingRegime";

const CONTENT_LABELS: Record<string, string> = {
  importance: "Importance",
  complexity: "Complexity",
  intensity: "Intensity",
  novelty: "Novelty",
  emotion: "Emotion",
  connectivity: "Connectivity",
  narrativity: "Narrativity",
  density: "Density",
};

export function DebugPanel() {
  const attentionMode = useReaderStore((s) => s.attentionMode);
  const attention = useReaderStore((s) => s.attention);
  const setAttentionMode = useReaderStore((s) => s.setAttentionMode);
  const setAttention = useReaderStore((s) => s.setAttention);
  const adaptiveRendering = useReaderStore((s) => s.adaptiveRendering);
  const toggleDebugPanel = useReaderStore((s) => s.toggleDebugPanel);
  const { unit, regime, visual, durationMs } = useReadingEngine();

  function onManualChange(key: keyof typeof attention, value: number) {
    if (attentionMode !== "manual") setAttentionMode("manual");
    setAttention({ [key]: value });
  }

  return (
    <div className="debug-panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>Debug panel</h2>
        <button className="icon-button" style={{ width: "2rem", height: "2rem" }} onClick={toggleDebugPanel} aria-label="Chiudi">
          ×
        </button>
      </div>

      <div className="debug-section">
        <h3>Current unit</h3>
        <p style={{ color: "var(--text-secondary)", fontStyle: "italic" }}>{unit?.text ?? "—"}</p>
      </div>

      <div className="debug-section">
        <h3>Content variables</h3>
        {unit &&
          SEMANTIC_SCALAR_KEYS.map((key) => (
            <div className="debug-row" key={key}>
              <span>{CONTENT_LABELS[key]}</span>
              <span>{unit[key].toFixed(2)}</span>
            </div>
          ))}
      </div>

      <div className="debug-section">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem" }}>
          <h3 style={{ margin: 0 }}>User variables</h3>
          <button
            className="pill-toggle"
            data-active={attentionMode === "manual"}
            onClick={() => setAttentionMode(attentionMode === "auto" ? "manual" : "auto")}
          >
            {attentionMode === "auto" ? "Auto (simulata)" : "Manuale"}
          </button>
        </div>
        <VariableSlider label="Attention" value={attention.estimatedAttention} onChange={(v) => onManualChange("estimatedAttention", v)} />
        <VariableSlider label="Fatigue" value={attention.fatigue} onChange={(v) => onManualChange("fatigue", v)} />
        <VariableSlider label="Engagement" value={attention.engagement} onChange={(v) => onManualChange("engagement", v)} />
      </div>

      <div className="debug-section">
        <h3>Derived values</h3>
        <div className="debug-row">
          <span>Adaptive rendering</span>
          <span>{adaptiveRendering ? "ON" : "OFF"}</span>
        </div>
        <div className="debug-row">
          <span>Regime</span>
          <span>{regime ? REGIME_LABELS[regime] : "—"}</span>
        </div>
        <div className="debug-row">
          <span>Duration</span>
          <span>{durationMs} ms</span>
        </div>
        {visual && (
          <>
            <div className="debug-row">
              <span>Layout</span>
              <span>{visual.layout}</span>
            </div>
            <div className="debug-row">
              <span>Font size</span>
              <span>{visual.fontSize.toFixed(2)} rem</span>
            </div>
            <div className="debug-row">
              <span>Chunk scale</span>
              <span>{visual.chunkScale.toFixed(2)}</span>
            </div>
            <div className="debug-row">
              <span>Context visibility</span>
              <span>{visual.contextVisibility.toFixed(2)}</span>
            </div>
            <div className="debug-row">
              <span>Motion amount</span>
              <span>{visual.motionAmount.toFixed(2)}</span>
            </div>
            <div className="debug-row">
              <span>Whitespace</span>
              <span>{visual.surroundingWhitespace.toFixed(2)}</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
