# Risorse open source e API usate

## Dati
| Risorsa | Licenza | Uso in Orbit |
|---|---|---|
| [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API) | CC0 (dati core) | ricerca artisti, crediti per registrazione, link esterni |
| [Genius API](https://docs.genius.com/) | gratuita, token personale; non open source | crediti producer/writer/performance (opzionale) |
| [Deezer API](https://developers.deezer.com/api) | gratuita, non open source | foto artista |
| [Discogs API](https://www.discogs.com/developers) | gratuita con token | candidata per crediti di ingegneri (non integrata) |
| [Wikidata](https://www.wikidata.org/) | CC0 | candidata per collegare identità tra fonti (non integrata) |

## Librerie (tutte Apache 2.0 salvo dove indicato)
| Libreria | Uso |
|---|---|
| Jetpack Compose (Google) | UI dichiarativa e canvas per blob, cerchi e grafo |
| Kotlin + coroutines (JetBrains) | linguaggio e concorrenza |
| kotlinx.serialization | parsing JSON |
| OkHttp (Square) | client HTTP |
| Coil | caricamento immagini in Compose |
| Room | database locale delle liste |
| Paparazzi (Cash App) | screenshot test senza emulatore |
| Inter Tight (Rsms / Google Fonts) | carattere, licenza OFL |

## Alternative valutate
- **Grafo:** Graphview/Compose-Graph esistono, ma il layout a fillotassi su Canvas dà la resa "poster" voluta e costa meno di una dipendenza.
- **Neo4j/Cytoscape:** utili solo con un backend; qui l'app è standalone.
- **Scraping Genius/Instagram:** escluso per termini d'uso e fragilità.
