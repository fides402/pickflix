# Orbit: requisiti per lo sviluppo

App Android standalone (nessun backend nostro) per esplorare la rete di collaboratori di un artista e costruire liste di contatti.

## 1. Prodotto
| Id | Requisito | Stato |
|---|---|---|
| P1 | Cercare un artista per nome | fatto (MusicBrainz) |
| P2 | Grafo dei collaboratori con ruolo, brani in comune e anno | fatto |
| P3 | Filtro per ruolo: producer, mixing, engineer, featuring, writer, performer | fatto |
| P4 | Dettaglio persona con brani, link social/streaming e fonti | fatto |
| P5 | Esplorare la rete di un collaboratore (livelli successivi) e tornare indietro | fatto |
| P6 | Liste salvate offline, segna "contattato", nascondi contattati, esporta CSV | fatto |
| P7 | Foto artista | fatto (Deezer, in bianco e nero, con fallback a iniziali) |
| P8 | Crediti Genius (producer, writer, ruoli custom) con token dell'utente | fatto, opzionale |
| P9 | Percorso più breve tra due artisti ("come arrivo a X?") | da fare |
| P10 | Import contatti/Gmail e tracking aperture | fuori ambito: richiede backend |

## 2. Dati: cosa serve per averli affidabili
- **Identità canonica:** MusicBrainz (CC0). Ogni persona ha un MBID stabile.
- **Crediti dei brani:** MusicBrainz (producer, mix, engineer) + Genius API (producer, writer, featured, performance custom). Le due fonti si fondono per nome normalizzato: una persona conta una volta sola.
- **Limiti da rispettare:** MusicBrainz 1 richiesta/secondo con User-Agent identificabile (gestito); Genius richiede token personale (Impostazioni); Deezer solo per le immagini.
- **Nessuno scraping HTML.** Genius lo vieta nei termini ed è fragile; si usa l'API ufficiale.
- **Copertura:** il grafo analizza fino a 500 registrazioni per artista e fino a 60 brani Genius. Sono parametri in `OrbitViewModel`.

## 3. Tecnici
- Android 8.0+ (minSdk 26), target 35. Kotlin 2.0, Jetpack Compose, coroutine.
- Rete: OkHttp + kotlinx.serialization. Persistenza: Room. Immagini: Coil.
- Permesso unico: `INTERNET`.
- Build: JDK 17, Android SDK 35, Gradle 8.10 (wrapper incluso).
- Test UI: Paparazzi genera screenshot delle schermate su JVM (`./gradlew :app:recordPaparazziDebug`), senza emulatore.
- CI: GitHub Actions (`.github/workflows/android.yml`) compila l'APK e verifica gli screenshot.

## 4. Design
- Linguaggio dai tre poster di riferimento: carta crema con grana e blob sfocati (ricerca), cerchi tangenti su giallo (rete), anelli concentrici su oliva (liste).
- Un solo carattere: Inter Tight variabile (OFL). Titoli stretti in maiuscolo, micro-etichette spaziate.
- Niente ombre, ripple, angoli arrotondati: forme piatte e cerchi pieni senza contorno.

## 5. Rischi aperti
1. MusicBrainz copre meno bene le uscite recenti e i crediti hip-hop rispetto a Genius: per questo Genius è previsto.
2. Le foto Deezer vengono trovate per nome esatto: omonimi o nomi d'arte possono restare senza foto.
3. Pubblicare su Play Store richiede firma release, privacy policy e attribuzione delle fonti dati.
