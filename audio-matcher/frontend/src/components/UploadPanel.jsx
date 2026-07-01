import { useState } from "react";
import { createJob } from "../api.js";

export default function UploadPanel({ topology, pluginIds, onJobCreated }) {
  const [referenceFile, setReferenceFile] = useState(null);
  const [sampleFile, setSampleFile] = useState(null);
  const [goalText, setGoalText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!referenceFile || !sampleFile) {
      setError("Carica sia il file di riferimento che il campione da trasformare.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const { job_id } = await createJob({ referenceFile, sampleFile, goalText, topology, pluginIds });
      onJobCreated(job_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="panel" onSubmit={handleSubmit}>
      <h3>1. Carica reference e campione</h3>
      <label>
        Reference (il suono da imitare)
        <input type="file" accept="audio/*" onChange={(e) => setReferenceFile(e.target.files[0])} />
      </label>
      <label>
        Campione da trasformare
        <input type="file" accept="audio/*" onChange={(e) => setSampleFile(e.target.files[0])} />
      </label>
      <label>
        Obiettivo (testo libero per l&apos;LLM)
        <textarea
          value={goalText}
          onChange={(e) => setGoalText(e.target.value)}
          placeholder="es: ricrea la sonorità di questo drum loop, più caldo e punchy"
        />
      </label>
      {error && <p className="error">{error}</p>}
      <button type="submit" disabled={submitting}>
        {submitting ? "Avvio..." : "Avvia matching"}
      </button>
    </form>
  );
}
