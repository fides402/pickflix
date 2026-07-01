import { useEffect, useState } from "react";
import { fetchFreeModels } from "../api.js";

export default function ModelSelector() {
  const [models, setModels] = useState([]);
  const [defaultModel, setDefaultModel] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchFreeModels()
      .then((data) => {
        setModels(data.models);
        setDefaultModel(data.default);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">Free model list unavailable: {error}</p>;

  return (
    <div className="panel">
      <h3>Modello LLM (orchestrazione)</h3>
      <p className="hint">
        Lista aggiornata dal vivo da OpenRouter (solo modelli con prezzo $0) — nessun ID inventato.
      </p>
      <select defaultValue={defaultModel}>
        {models.map((m) => (
          <option key={m.id} value={m.id}>
            {m.name} {m.id === defaultModel ? "(default)" : ""}
          </option>
        ))}
      </select>
      <p className="hint">{models.length} modelli gratuiti disponibili ora.</p>
    </div>
  );
}
