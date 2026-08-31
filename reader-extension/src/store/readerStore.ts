import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ReadingDocument } from "../models/ReadingDocument";
import type { SemanticUnit } from "../models/SemanticUnit";
import type { AttentionState } from "../models/AttentionState";
import type { AttentionMode } from "../engine/attentionEngine";
import { simulateAttentionTick, resetAttentionState } from "../engine/attentionEngine";
import { chromeStorage } from "./chromeStorage";
import { DEFAULT_FONT_FAMILY, type FontFamilyId } from "../styles/fonts";

export type Theme = "light" | "dark" | "system";

export type LiveSessionStatus = {
  /** true once a ChatGPT live import has started for the current document */
  active: boolean;
  /** a round request is currently in flight */
  generating: boolean;
  hasMore: boolean;
  error: string | null;
  roundsDone: number;
  roundsTotal: number;
};

const IDLE_LIVE_SESSION: LiveSessionStatus = {
  active: false,
  generating: false,
  hasMore: false,
  error: null,
  roundsDone: 0,
  roundsTotal: 0,
};

export type ReaderSettings = {
  theme: Theme;
  fontFamily: FontFamilyId;
  fontScale: number;
  lineHeightScale: number;
  reducedMotion: boolean;
};

type ReaderState = {
  document: ReadingDocument | null;
  currentIndex: number;
  isPlaying: boolean;
  speedMultiplier: number;
  adaptiveRendering: boolean;
  attentionMode: AttentionMode;
  attention: AttentionState;
  sessionStartMs: number;
  debugPanelOpen: boolean;
  settings: ReaderSettings;
  liveSession: LiveSessionStatus;

  loadDocument: (document: ReadingDocument) => void;
  appendUnits: (units: SemanticUnit[]) => void;
  setLiveSessionStatus: (partial: Partial<LiveSessionStatus>) => void;
  resetLiveSession: () => void;
  setCurrentIndex: (index: number) => void;
  next: () => void;
  previous: () => void;
  restart: () => void;
  play: () => void;
  pause: () => void;
  togglePlay: () => void;
  setSpeed: (multiplier: number) => void;
  setAdaptiveRendering: (enabled: boolean) => void;
  setAttentionMode: (mode: AttentionMode) => void;
  setAttention: (partial: Partial<AttentionState>) => void;
  tickAttention: (elapsedMs: number) => void;
  toggleDebugPanel: () => void;
  setDebugPanelOpen: (open: boolean) => void;
  updateSettings: (partial: Partial<ReaderSettings>) => void;
};

type PersistedReaderState = Pick<
  ReaderState,
  "document" | "currentIndex" | "speedMultiplier" | "adaptiveRendering" | "settings"
>;

export const useReaderStore = create<ReaderState>()(
  persist<ReaderState, [], [], PersistedReaderState>(
    (set, get) => ({
      document: null,
      currentIndex: 0,
      isPlaying: false,
      speedMultiplier: 1,
      adaptiveRendering: true,
      attentionMode: "auto",
      attention: resetAttentionState(),
      sessionStartMs: Date.now(),
      debugPanelOpen: false,
      settings: {
        theme: "system",
        fontFamily: DEFAULT_FONT_FAMILY,
        fontScale: 1,
        lineHeightScale: 1,
        reducedMotion: false,
      },
      liveSession: IDLE_LIVE_SESSION,

      loadDocument: (document) =>
        set({
          document,
          currentIndex: 0,
          isPlaying: false,
          attention: resetAttentionState(),
          sessionStartMs: Date.now(),
          adaptiveRendering: document.hasSemanticScores ? true : false,
          liveSession: IDLE_LIVE_SESSION,
        }),

      appendUnits: (units) => {
        const doc = get().document;
        if (!doc) return;
        set({ document: { ...doc, units: [...doc.units, ...units] } });
      },

      setLiveSessionStatus: (partial) =>
        set((s) => ({ liveSession: { ...s.liveSession, ...partial } })),

      resetLiveSession: () => set({ liveSession: IDLE_LIVE_SESSION }),

      setCurrentIndex: (index) => {
        const doc = get().document;
        if (!doc) return;
        const clamped = Math.min(Math.max(0, index), doc.units.length - 1);
        set({ currentIndex: clamped });
      },

      next: () => {
        const { document, currentIndex } = get();
        if (!document) return;
        if (currentIndex >= document.units.length - 1) {
          set({ isPlaying: false });
          return;
        }
        set({ currentIndex: currentIndex + 1 });
      },

      previous: () => {
        const { currentIndex } = get();
        set({ currentIndex: Math.max(0, currentIndex - 1) });
      },

      restart: () => set({ currentIndex: 0, isPlaying: false }),

      play: () => {
        if (!get().document) return;
        set({ isPlaying: true });
      },
      pause: () => set({ isPlaying: false }),
      togglePlay: () => {
        if (!get().document) return;
        set((s) => ({ isPlaying: !s.isPlaying }));
      },

      setSpeed: (multiplier) => set({ speedMultiplier: Math.min(3, Math.max(0.4, multiplier)) }),

      setAdaptiveRendering: (enabled) => set({ adaptiveRendering: enabled }),

      setAttentionMode: (mode) => set({ attentionMode: mode }),

      setAttention: (partial) =>
        set((s) => ({ attention: { ...s.attention, ...partial } })),

      tickAttention: (elapsedMs) => {
        const { attentionMode, attention, document, currentIndex, sessionStartMs } = get();
        if (attentionMode !== "auto") return;
        const unit = document?.units[currentIndex];
        const next = simulateAttentionTick(attention, elapsedMs, Date.now() - sessionStartMs, unit);
        set({ attention: next });
      },

      toggleDebugPanel: () => set((s) => ({ debugPanelOpen: !s.debugPanelOpen })),
      setDebugPanelOpen: (open) => set({ debugPanelOpen: open }),

      updateSettings: (partial) =>
        set((s) => ({ settings: { ...s.settings, ...partial } })),
    }),
    {
      name: "adaptive-reader-state",
      storage: {
        getItem: async (name) => {
          const value = await chromeStorage.getItem(name);
          return value ? JSON.parse(value) : null;
        },
        setItem: async (name, value) => {
          await chromeStorage.setItem(name, JSON.stringify(value));
        },
        removeItem: async (name) => {
          await chromeStorage.removeItem(name);
        },
      },
      partialize: (state): PersistedReaderState => ({
        document: state.document,
        currentIndex: state.currentIndex,
        speedMultiplier: state.speedMultiplier,
        adaptiveRendering: state.adaptiveRendering,
        settings: state.settings,
      }),
    },
  ),
);
