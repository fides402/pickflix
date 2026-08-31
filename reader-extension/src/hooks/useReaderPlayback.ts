import { useEffect } from "react";
import { useReaderStore } from "../store/readerStore";
import { useReadingEngine } from "./useReadingEngine";

/** Advances to the next unit after durationMs while playing. */
export function useReaderPlayback() {
  const isPlaying = useReaderStore((s) => s.isPlaying);
  const currentIndex = useReaderStore((s) => s.currentIndex);
  const next = useReaderStore((s) => s.next);
  const { durationMs } = useReadingEngine();

  useEffect(() => {
    if (!isPlaying || durationMs <= 0) return;
    const timer = window.setTimeout(() => next(), durationMs);
    return () => window.clearTimeout(timer);
    // currentIndex is included so a manual prev/next while playing restarts the countdown for the new unit
  }, [isPlaying, durationMs, currentIndex, next]);
}
