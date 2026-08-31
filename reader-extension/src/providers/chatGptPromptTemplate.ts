/**
 * Builds a ready-to-paste prompt that asks an external LLM (ChatGPT or any
 * other) to produce a scored JSON matching the app's import schema for a
 * given piece of text. The user copies this, runs it externally, and
 * imports the resulting JSON back in via the JSON importer — this keeps the
 * extension itself free of any AI integration, per the provider boundary.
 */
export function buildChatGptPrompt(text: string, title: string): string {
  const truncated = text.length > 6000 ? `${text.slice(0, 6000)}\n[...testo troncato per lunghezza...]` : text;

  return `Sei un analista editoriale. Suddividi il testo qui sotto in "semantic units" (frasi brevi o mezze frasi, ognuna un'unità di lettura coerente) e per ciascuna assegna 8 punteggi normalizzati tra 0 e 1:

- importance: quanto è importante da capire/ricordare
- complexity: quanto richiede elaborazione cognitiva
- intensity: quanto il momento è forte/drammatico
- novelty: quanto introduce qualcosa di nuovo
- emotion: carica emotiva
- connectivity: quanto dipende da/collega concetti precedenti
- narrativity: 0 = spiegazione astratta, 1 = azione/narrazione/dialogo
- density: quanta informazione per unità di testo

Rispondi SOLO con un JSON valido in questo formato esatto, senza testo aggiuntivo:

{
  "title": "${title || "Titolo"}",
  "author": "Autore (se noto, altrimenti ometti il campo)",
  "units": [
    {
      "id": "1",
      "text": "porzione di testo originale, invariata",
      "importance": 0.0,
      "complexity": 0.0,
      "intensity": 0.0,
      "novelty": 0.0,
      "emotion": 0.0,
      "connectivity": 0.0,
      "narrativity": 0.0,
      "density": 0.0
    }
  ]
}

Testo da analizzare:
"""
${truncated}
"""`;
}
