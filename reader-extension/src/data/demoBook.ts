import type { SemanticUnit } from "../models/SemanticUnit";
import type { ReadingDocument } from "../models/ReadingDocument";

/**
 * Original, public-domain-safe demo text written for this project: a fictional
 * account of an early-1900s polar expedition. It deliberately mixes narrative
 * action, dense exposition, emotional beats and quiet reflection so the five
 * reading regimes (flow, focus, reveal, recovery, cruise) each get a chance
 * to show up while playing the demo.
 */
const units: SemanticUnit[] = [
  u("d1", "La nave salpò all'alba,", 0.3, 0.1, 0.3, 0.4, 0.2, 0.1, 0.9, 0.2),
  u("d2", "quando il porto era ancora avvolto nella nebbia.", 0.25, 0.15, 0.25, 0.3, 0.25, 0.3, 0.85, 0.25),
  u("d3", "Il capitano Halvorsen non si voltò a guardare la costa.", 0.4, 0.2, 0.4, 0.3, 0.4, 0.3, 0.9, 0.25),
  u("d4", "Aveva promesso a se stesso di non farlo mai più.", 0.45, 0.25, 0.45, 0.35, 0.6, 0.5, 0.85, 0.25),
  u("d5", "Diciassette uomini, una nave di legno rinforzato,", 0.5, 0.3, 0.35, 0.6, 0.2, 0.3, 0.7, 0.4),
  u("d6", "e centosessanta giorni di provviste per un viaggio che nessuno aveva mai completato.", 0.7, 0.35, 0.5, 0.7, 0.3, 0.4, 0.6, 0.5),
  u("d7", "Il ghiaccio marino non è semplicemente acqua congelata.", 0.6, 0.5, 0.2, 0.7, 0.05, 0.2, 0.1, 0.6),
  u("d8", "È una struttura viva, che respira e si muove con le maree,", 0.55, 0.55, 0.25, 0.6, 0.1, 0.4, 0.15, 0.65),
  u("d9", "capace di stritolare uno scafo in poche ore", 0.75, 0.5, 0.7, 0.5, 0.2, 0.5, 0.2, 0.55),
  u("d10", "o di aprirsi in un canale navigabile nel giro di una notte.", 0.6, 0.5, 0.4, 0.5, 0.1, 0.5, 0.2, 0.55),
  u("d11", "Per orientarsi, l'equipaggio non poteva fidarsi della sola bussola:", 0.65, 0.65, 0.3, 0.65, 0.05, 0.4, 0.15, 0.7),
  u("d12", "vicino ai poli, l'ago magnetico oscilla, esita, a volte punta nella direzione sbagliata,", 0.7, 0.75, 0.35, 0.7, 0.1, 0.5, 0.15, 0.75),
  u("d13", "perché il polo magnetico terrestre non coincide con quello geografico.", 0.75, 0.8, 0.3, 0.75, 0.05, 0.6, 0.05, 0.8),
  u("d14", "Halvorsen aveva imparato a leggere le stelle prima ancora di leggere le lettere.", 0.5, 0.3, 0.3, 0.3, 0.35, 0.3, 0.6, 0.35),
  u("d15", "Il diciannovesimo giorno, il cielo cambiò colore.", 0.5, 0.2, 0.6, 0.55, 0.3, 0.2, 0.85, 0.3),
  u("d16", "Da un grigio uniforme a un verde metallico, innaturale.", 0.5, 0.25, 0.65, 0.6, 0.35, 0.3, 0.75, 0.3),
  u("d17", "Nessuno dell'equipaggio aveva mai visto un cielo così.", 0.45, 0.2, 0.6, 0.55, 0.4, 0.2, 0.8, 0.25),
  u("d18", "\"Tempesta\", disse solo il secondo ufficiale.", 0.55, 0.15, 0.7, 0.4, 0.4, 0.3, 0.9, 0.2),
  u("d19", "In un'ora il vento passò da dieci a settanta nodi.", 0.6, 0.35, 0.85, 0.5, 0.35, 0.4, 0.75, 0.45),
  u("d20", "Le onde smisero di essere onde e diventarono pareti.", 0.6, 0.3, 0.9, 0.5, 0.5, 0.3, 0.8, 0.35),
  u("d21", "Halvorsen legò se stesso al timone con una corda bagnata,", 0.65, 0.25, 0.85, 0.35, 0.6, 0.5, 0.9, 0.3),
  u("d22", "e per sei ore non lasciò la presa nemmeno per un secondo.", 0.7, 0.25, 0.9, 0.35, 0.7, 0.6, 0.9, 0.3),
  u("d23", "Quando il vento cadde, all'improvviso, il silenzio fece più paura della tempesta.", 0.7, 0.3, 0.85, 0.6, 0.65, 0.4, 0.85, 0.35),
  u("d24", "Fu allora che qualcuno gridò: \"Terra!\"", 0.85, 0.15, 0.9, 0.9, 0.6, 0.3, 0.95, 0.25),
  u("d25", "Ma non era terra.", 0.8, 0.3, 0.75, 0.95, 0.55, 0.7, 0.7, 0.35),
  u("d26", "Era una parete di ghiaccio alta come una cattedrale,", 0.85, 0.3, 0.8, 0.9, 0.5, 0.6, 0.55, 0.4),
  u("d27", "che nessuna mappa conosciuta segnalava in quel punto dell'oceano.", 0.9, 0.45, 0.7, 0.95, 0.3, 0.6, 0.3, 0.55),
  u("d28", "Avevano scoperto qualcosa che non aveva ancora un nome.", 0.9, 0.3, 0.75, 1.0, 0.55, 0.5, 0.6, 0.35),
  u("d29", "Halvorsen rimase in silenzio per un tempo che nessuno seppe misurare.", 0.6, 0.2, 0.6, 0.5, 0.7, 0.4, 0.75, 0.25),
  u("d30", "Pensò a sua figlia, alla sua età, a quanto fosse lontana da quel momento.", 0.4, 0.15, 0.5, 0.3, 0.85, 0.3, 0.7, 0.25),
  u("d31", "Non l'aveva più vista crescere da tre anni.", 0.45, 0.15, 0.45, 0.3, 0.9, 0.4, 0.65, 0.2),
  u("d32", "Ogni scoperta ha un prezzo che non compare su nessuna mappa.", 0.6, 0.35, 0.4, 0.4, 0.7, 0.5, 0.3, 0.4),
  u("d33", "Lo pagano le persone lasciate a casa, non chi parte.", 0.55, 0.3, 0.4, 0.35, 0.75, 0.5, 0.35, 0.35),
  u("d34", "Il corpo umano, esposto a temperature sotto i -30°C,", 0.65, 0.55, 0.3, 0.5, 0.15, 0.3, 0.1, 0.6),
  u("d35", "reagisce restringendo i vasi sanguigni delle estremità,", 0.6, 0.6, 0.25, 0.5, 0.05, 0.4, 0.05, 0.65),
  u("d36", "per proteggere gli organi vitali a costo delle dita e del naso.", 0.7, 0.6, 0.4, 0.55, 0.1, 0.5, 0.15, 0.65),
  u("d37", "È lo stesso meccanismo che, in eccesso, porta al congelamento.", 0.65, 0.65, 0.35, 0.55, 0.1, 0.6, 0.1, 0.7),
  u("d38", "L'equipaggio lo sapeva, e controllava le proprie mani ogni ora,", 0.55, 0.4, 0.3, 0.35, 0.2, 0.5, 0.4, 0.5),
  u("d39", "cercando quel primo, innocuo, pizzicore bianco sulla pelle.", 0.5, 0.4, 0.35, 0.4, 0.25, 0.5, 0.35, 0.5),
  u("d40", "Decisero di costeggiare la parete di ghiaccio verso ovest.", 0.4, 0.2, 0.35, 0.3, 0.15, 0.4, 0.65, 0.35),
  u("d41", "Per tre giorni non successe nulla.", 0.2, 0.1, 0.15, 0.2, 0.1, 0.3, 0.6, 0.2),
  u("d42", "Il mare era piatto, il cielo era bianco, il tempo sembrava essersi fermato.", 0.25, 0.15, 0.15, 0.2, 0.15, 0.2, 0.5, 0.25),
  u("d43", "Poi la parete si aprì in un varco largo quanto la nave.", 0.7, 0.25, 0.7, 0.8, 0.4, 0.5, 0.85, 0.35),
  u("d44", "Oltre il varco, un'acqua così immobile da sembrare vetro.", 0.6, 0.2, 0.55, 0.75, 0.5, 0.4, 0.7, 0.3),
  u("d45", "E sull'altra sponda, una colonia di uccelli mai catalogata prima.", 0.85, 0.3, 0.6, 0.95, 0.5, 0.4, 0.6, 0.4),
  u("d46", "Migliaia di ali bianche si alzarono insieme, come un unico corpo.", 0.7, 0.2, 0.75, 0.7, 0.7, 0.3, 0.85, 0.3),
  u("d47", "Nessuno dell'equipaggio parlò per diversi minuti.", 0.5, 0.15, 0.55, 0.4, 0.75, 0.3, 0.7, 0.2),
  u("d48", "Alcune scoperte non hanno bisogno di essere spiegate, solo viste.", 0.6, 0.2, 0.5, 0.5, 0.7, 0.3, 0.4, 0.3),
  u("d49", "Il ritorno fu, sorprendentemente, più semplice dell'andata.", 0.35, 0.15, 0.25, 0.2, 0.3, 0.3, 0.7, 0.25),
  u("d50", "Il vento li spinse verso casa come se avesse fretta quanto loro.", 0.3, 0.15, 0.3, 0.25, 0.4, 0.3, 0.75, 0.25),
  u("d51", "Halvorsen scrisse nel diario di bordo solo una frase, quella sera:", 0.55, 0.15, 0.4, 0.3, 0.5, 0.4, 0.6, 0.25),
  u("d52", "\"Abbiamo trovato qualcosa. Non eravamo pronti a trovarlo.\"", 0.75, 0.2, 0.6, 0.6, 0.6, 0.5, 0.5, 0.3),
  u("d53", "Non tutte le mappe finite servono a orientarsi.", 0.5, 0.3, 0.3, 0.3, 0.4, 0.4, 0.2, 0.4),
  u("d54", "Alcune servono solo a ricordarci quanto poco sappiamo ancora.", 0.55, 0.3, 0.35, 0.35, 0.5, 0.4, 0.2, 0.4),
  u("d55", "In porto, tre mesi dopo, nessuno chiese a Halvorsen cosa avesse visto.", 0.3, 0.15, 0.2, 0.2, 0.4, 0.3, 0.5, 0.2),
  u("d56", "Bastava guardarlo negli occhi per capire che era cambiato.", 0.35, 0.15, 0.3, 0.25, 0.55, 0.3, 0.45, 0.2),
];

function u(
  id: string,
  text: string,
  importance: number,
  complexity: number,
  intensity: number,
  novelty: number,
  emotion: number,
  connectivity: number,
  narrativity: number,
  density: number,
): SemanticUnit {
  return { id, text, importance, complexity, intensity, novelty, emotion, connectivity, narrativity, density };
}

export const demoBook: ReadingDocument = {
  title: "Il varco",
  author: "Adaptive Reader Demo",
  units,
  hasSemanticScores: true,
  source: "demo",
};
