import { useEffect, useState } from "react";
import { fetchPlugins } from "../api.js";

const SIMULATED_STAGE_TYPES = ["eq3", "compressor", "saturation", "reverb"];

export default function PluginSelector({ selectedTopology, onChangeTopology, selectedPluginIds, onChangePluginIds }) {
  const [scanned, setScanned] = useState({ plugins: [], scan_paths: [] });
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPlugins()
      .then(setScanned)
      .catch((e) => setError(e.message));
  }, []);

  function toggleStage(stage) {
    if (selectedTopology.includes(stage)) {
      onChangeTopology(selectedTopology.filter((s) => s !== stage));
    } else {
      onChangeTopology([...selectedTopology, stage]);
    }
  }

  function togglePlugin(id) {
    if (selectedPluginIds.includes(id)) {
      onChangePluginIds(selectedPluginIds.filter((p) => p !== id));
    } else {
      onChangePluginIds([...selectedPluginIds, id]);
    }
  }

  const hasRealSelection = selectedPluginIds.length > 0;
  const hasSimulatedSelection = selectedTopology.length > 0;

  return (
    <div className="panel">
      <h3>Plugin da usare nella catena (a monte)</h3>
      <p className="hint">
        Scegli o i tuoi plugin VST3 reali (elaborazione vera, tramite DawDreamer) o i tipi simulati qui
        sotto — non entrambi insieme in questa versione. Lascia tutto deselezionato per far proporre la
        topologia all&apos;LLM.
      </p>

      <h4>Plugin VST3 reali trovati sulla macchina</h4>
      {error && <p className="error">Scan non disponibile: {error}</p>}
      {!error && scanned.plugins.length === 0 && (
        <p className="hint">
          Nessun plugin trovato in {scanned.scan_paths?.join(", ") || "..."} — verrà usato il motore DSP
          simulato per questa demo (vedi limitazioni nel README).
        </p>
      )}
      {!error && scanned.plugins.length > 0 && (
        <div className="stage-checkboxes">
          {scanned.plugins.map((p) => (
            <label key={p.id} title={`${p.vendor} — ${p.metadata_source}`}>
              <input
                type="checkbox"
                checked={selectedPluginIds.includes(p.id)}
                disabled={hasSimulatedSelection}
                onChange={() => togglePlugin(p.id)}
              />
              {p.name}
            </label>
          ))}
        </div>
      )}

      <h4>Tipi simulati (motore DSP, per demo/test senza plugin reali)</h4>
      <div className="stage-checkboxes">
        {SIMULATED_STAGE_TYPES.map((stage) => (
          <label key={stage}>
            <input
              type="checkbox"
              checked={selectedTopology.includes(stage)}
              disabled={hasRealSelection}
              onChange={() => toggleStage(stage)}
            />
            {stage}
          </label>
        ))}
      </div>
    </div>
  );
}
