import { useEffect, useState } from "react";
import { fetchPlugins } from "../api.js";

const SIMULATED_STAGE_TYPES = ["eq3", "compressor", "saturation", "reverb"];

export default function PluginSelector({ selectedTopology, onChangeTopology }) {
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

  return (
    <div className="panel">
      <h3>Plugin da usare nella catena (a monte)</h3>
      <p className="hint">
        Lascia tutto deselezionato per far proporre la topologia all&apos;LLM in base al riferimento.
      </p>
      <div className="stage-checkboxes">
        {SIMULATED_STAGE_TYPES.map((stage) => (
          <label key={stage}>
            <input
              type="checkbox"
              checked={selectedTopology.includes(stage)}
              onChange={() => toggleStage(stage)}
            />
            {stage}
          </label>
        ))}
      </div>

      <h4>Plugin VST3 reali trovati sulla macchina</h4>
      {error && <p className="error">Scan non disponibile: {error}</p>}
      {!error && scanned.plugins.length === 0 && (
        <p className="hint">
          Nessun plugin trovato in {scanned.scan_paths?.join(", ") || "..."} — verrà usato il motore DSP
          simulato per questa demo (vedi limitazioni nel README).
        </p>
      )}
      {!error && scanned.plugins.length > 0 && (
        <ul>
          {scanned.plugins.map((p) => (
            <li key={p.id}>
              {p.name} ({p.vendor}) — {p.metadata_source}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
