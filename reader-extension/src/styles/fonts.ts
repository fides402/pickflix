export type FontFamilyId = "literata" | "source-serif" | "lora";

export type FontOption = {
  id: FontFamilyId;
  label: string;
  description: string;
  cssFamily: string;
};

/**
 * Curated, free, self-hosted (no CDN) serif families chosen for long-form
 * reading comfort. Bundled via @fontsource so the extension works fully
 * offline and never violates the MV3 CSP by fetching remote fonts.
 */
export const FONT_OPTIONS: FontOption[] = [
  {
    id: "literata",
    label: "Literata",
    description: "Serif editoriale calda, disegnata per la lettura di libri lunghi.",
    cssFamily: "'Literata', 'Georgia', serif",
  },
  {
    id: "source-serif",
    label: "Source Serif 4",
    description: "Serif contemporanea, alta leggibilità, tono più neutro.",
    cssFamily: "'Source Serif 4', 'Georgia', serif",
  },
  {
    id: "lora",
    label: "Lora",
    description: "Serif con un tratto calligrafico morbido, ottima per narrativa.",
    cssFamily: "'Lora', 'Georgia', serif",
  },
];

export const UI_FONT_FAMILY = "'Inter', system-ui, sans-serif";

export const DEFAULT_FONT_FAMILY: FontFamilyId = "literata";
