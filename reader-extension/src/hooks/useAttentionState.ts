import { useEffect, useRef } from "react";
import { useReaderStore } from "../store/readerStore";

const TICK_MS = 800;

/** Drives the simulated-automatic attention mode with a periodic tick. */
export function useAttentionState() {
  const attentionMode = useReaderStore((s) => s.attentionMode);
  const isPlaying = useReaderStore((s) => s.isPlaying);
  const tickAttention = useReaderStore((s) => s.tickAttention);
  const lastTickRef = useRef(Date.now());

  useEffect(() => {
    if (attentionMode !== "auto" || !isPlaying) {
      lastTickRef.current = Date.now();
      return;
    }
    lastTickRef.current = Date.now();
    const interval = window.setInterval(() => {
      const now = Date.now();
      const elapsed = now - lastTickRef.current;
      lastTickRef.current = now;
      tickAttention(elapsed);
    }, TICK_MS);
    return () => window.clearInterval(interval);
  }, [attentionMode, isPlaying, tickAttention]);
}
