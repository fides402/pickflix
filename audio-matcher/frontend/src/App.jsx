import { useState } from "react";
import ModelSelector from "./components/ModelSelector.jsx";
import PluginSelector from "./components/PluginSelector.jsx";
import UploadPanel from "./components/UploadPanel.jsx";
import JobMonitor from "./components/JobMonitor.jsx";

export default function App() {
  const [topology, setTopology] = useState([]);
  const [pluginIds, setPluginIds] = useState([]);
  const [jobId, setJobId] = useState(null);

  return (
    <div className="app">
      <h1>Audio Reference Matcher</h1>
      <p className="hint">
        Carica un riferimento e un campione: un ottimizzatore CMA-ES adatta una catena di plugin per
        avvicinare il campione al riferimento, con un LLM (via OpenRouter, solo modelli gratuiti) che
        propone la topologia e riassume il risultato.
      </p>

      <ModelSelector />
      <PluginSelector
        selectedTopology={topology}
        onChangeTopology={setTopology}
        selectedPluginIds={pluginIds}
        onChangePluginIds={setPluginIds}
      />
      <UploadPanel topology={topology} pluginIds={pluginIds} onJobCreated={setJobId} />

      {jobId && <JobMonitor jobId={jobId} />}
    </div>
  );
}
