import { useMemo, useRef } from "react";
import { useReaderStore } from "../store/readerStore";
import { deriveRegime } from "../engine/regimeEngine";
import { deriveVisualState } from "../engine/visualEngine";
import { computeReadingFrame } from "../engine/readingEngine";
import type { SemanticUnit } from "../models/SemanticUnit";
import type { VisualState } from "../models/VisualState";
import type { ReadingRegime } from "../models/ReadingRegime";

export type ReadingEngineResult = {
  unit: SemanticUnit | undefined;
  regime: ReadingRegime | null;
  visual: VisualState | null;
  /** snapshotted once per unit so mid-unit attention tweaks don't reset the playback timer */
  durationMs: number;
};

/**
 * regime/visual react live to attention changes (so debug sliders update the
 * render immediately, per spec). durationMs is snapshotted once per unit so
 * a live-changing attention doesn't keep resetting the autoplay countdown.
 */
export function useReadingEngine(): ReadingEngineResult {
  const document = useReaderStore((s) => s.document);
  const currentIndex = useReaderStore((s) => s.currentIndex);
  const attention = useReaderStore((s) => s.attention);
  const speedMultiplier = useReaderStore((s) => s.speedMultiplier);
  const adaptiveRendering = useReaderStore((s) => s.adaptiveRendering);

  const unit = document?.units[currentIndex];

  const attentionRef = useRef(attention);
  attentionRef.current = attention;

  const regime = useMemo(
    () => (unit && adaptiveRendering ? deriveRegime(unit, attention) : unit ? "cruise" : null),
    [unit, attention, adaptiveRendering],
  );

  const visual = useMemo(() => {
    if (!unit || !regime) return null;
    if (!adaptiveRendering) {
      return computeReadingFrame(unit, attention, speedMultiplier, false).visual;
    }
    return deriveVisualState(unit, attention, regime);
  }, [unit, regime, attention, adaptiveRendering, speedMultiplier]);

  const durationMs = useMemo(() => {
    if (!unit) return 0;
    return computeReadingFrame(unit, attentionRef.current, speedMultiplier, adaptiveRendering).durationMs;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unit?.id, speedMultiplier, adaptiveRendering]);

  return { unit, regime, visual, durationMs };
}
