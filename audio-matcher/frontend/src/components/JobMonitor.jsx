import { useEffect, useState } from "react";
import { fetchJob, manifestUrl, containerManifestUrl, vstPresetUrl, audioUrl } from "../api.js";
import ConvergenceChart from "./ConvergenceChart.jsx";

const TERMINAL_STATES = new Set(["done", "failed"]);

export default function JobMonitor({ jobId }) {
  const [job, setJob] = useState(null);
  const [containerPluginId, setContainerPluginId] = useState("");

  useEffect(() => {
    let cancelled = false;
    let timer;

    async function poll() {
      try {
        const data = await fetchJob(jobId);
        if (cancelled) return;
        setJob(data);
        if (!TERMINAL_STATES.has(data.status)) {
          timer = setTimeout(poll, 1500);
        }
      } catch (e) {
        if (!cancelled) setJob({ status: "failed", error: e.message });
      }
    }
    poll();

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [jobId]);

  if (!job) return <p>Caricamento...</p>;

  return (
    <div className="panel">
      <h3>Job {jobId.slice(0, 8)}</h3>
      <p>
        Stato: <strong>{job.status}</strong>
        {job.error && <span className="error"> — {job.error}</span>}
      </p>
      {job.topology?.length > 0 && (
        <p>
          Topologia: {job.topology.join(" → ")}
          {job.topology_reasoning && <em> ({job.topology_reasoning})</em>}
        </p>
      )}
      <ConvergenceChart iterations={job.iterations} />
      {job.baseline_distance != null && (
        <p>
          Distanza iniziale (senza processing): {job.baseline_distance.toFixed(4)} → finale:{" "}
          {job.final_distance != null ? job.final_distance.toFixed(4) : "..."}
          {job.used_identity_fallback && (
            <em> (nessuna catena ha battuto il segnale grezzo: applicato fallback identità)</em>
          )}
        </p>
      )}
      {job.summary_text && <p className="summary">{job.summary_text}</p>}
      {job.status === "done" && (
        <div className="downloads">
          <a href={manifestUrl(jobId)} target="_blank" rel="noreferrer">
            Manifest catena (JSON)
          </a>
          <a href={containerManifestUrl(jobId)} target="_blank" rel="noreferrer">
            Container VST3 manifest
          </a>
          <a href={audioUrl(jobId)} download>
            Audio elaborato (.wav)
          </a>
        </div>
      )}
      {job.status === "done" && (
        <div className="panel" style={{ marginTop: 12 }}>
          <h4>Export .vstpreset diretto (sperimentale)</h4>
          <p className="hint">
            Richiede di aver compilato container-plugin/ e averlo aggiunto a PLUGIN_SCAN_PATHS. Inserisci
            l&apos;id con cui compare in GET /plugins.
          </p>
          <input
            type="text"
            placeholder="id del Container VST3 compilato"
            value={containerPluginId}
            onChange={(e) => setContainerPluginId(e.target.value)}
          />
          {containerPluginId && (
            <a href={vstPresetUrl(jobId, containerPluginId)} download>
              Scarica chain.vstpreset
            </a>
          )}
        </div>
      )}
    </div>
  );
}
