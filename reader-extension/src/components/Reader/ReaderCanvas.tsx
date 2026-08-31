import { useEffect, useRef, useState } from "react";
import { useReaderStore } from "../../store/readerStore";
import { useReadingEngine } from "../../hooks/useReadingEngine";
import { useReaderPlayback } from "../../hooks/useReaderPlayback";
import { useAttentionState } from "../../hooks/useAttentionState";
import { useLiveRoundPrefetch } from "../../hooks/useLiveRoundPrefetch";
import { SemanticUnitView } from "./SemanticUnitView";
import { ContextStack } from "./ContextStack";
import { ReaderControls } from "./ReaderControls";
import { TopBar } from "./TopBar";

const IDLE_HIDE_MS = 2200;

type Props = {
  onHome: () => void;
};

export function ReaderCanvas({ onHome }: Props) {
  const document = useReaderStore((s) => s.document);
  const currentIndex = useReaderStore((s) => s.currentIndex);
  const isPlaying = useReaderStore((s) => s.isPlaying);
  const togglePlay = useReaderStore((s) => s.togglePlay);
  const next = useReaderStore((s) => s.next);
  const previous = useReaderStore((s) => s.previous);
  const toggleDebugPanel = useReaderStore((s) => s.toggleDebugPanel);
  const settings = useReaderStore((s) => s.settings);
  const updateSettings = useReaderStore((s) => s.updateSettings);

  useReaderPlayback();
  useAttentionState();
  useLiveRoundPrefetch();
  const { unit, regime, visual } = useReadingEngine();

  const prefersReducedMotion =
    typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const reducedMotion = settings.reducedMotion || !!prefersReducedMotion;

  const [controlsVisible, setControlsVisible] = useState(true);
  const idleTimer = useRef<number | undefined>(undefined);
  // Touch devices have no hover/mousemove to bring controls back — auto-hiding
  // them there just makes them disappear with no obvious way to get them back.
  const isCoarsePointer =
    typeof window !== "undefined" && !!window.matchMedia?.("(pointer: coarse)").matches;

  const revealControls = () => {
    setControlsVisible(true);
    window.clearTimeout(idleTimer.current);
    if (isCoarsePointer) return;
    idleTimer.current = window.setTimeout(() => {
      if (isPlaying) setControlsVisible(false);
    }, IDLE_HIDE_MS);
  };

  useEffect(() => {
    revealControls();
    return () => window.clearTimeout(idleTimer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPlaying]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
      switch (e.code) {
        case "Space":
          e.preventDefault();
          togglePlay();
          break;
        case "ArrowRight":
          next();
          break;
        case "ArrowLeft":
          previous();
          break;
        case "ArrowUp":
          e.preventDefault();
          updateSettings({ fontScale: Math.min(1.6, settings.fontScale + 0.06) });
          break;
        case "ArrowDown":
          e.preventDefault();
          updateSettings({ fontScale: Math.max(0.75, settings.fontScale - 0.06) });
          break;
        case "Escape":
          revealControls();
          toggleDebugPanel();
          break;
        default:
          return;
      }
      revealControls();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [togglePlay, next, previous, settings.fontScale]);

  if (!document || !unit || !visual) return null;

  const previousUnits = document.units.slice(0, currentIndex);
  const nextUnits = document.units.slice(currentIndex + 1);

  return (
    <div
      className="app-shell"
      onMouseMove={revealControls}
      onClick={revealControls}
      onTouchStart={revealControls}
    >
      <TopBar visible={controlsVisible} regime={regime} onHome={onHome} />

      <div className="reader-canvas">
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1.4rem", width: "100%" }}>
          <ContextStack
            units={previousUnits}
            direction="above"
            layout={visual.layout}
            contextVisibility={visual.contextVisibility}
            fontFamily={settings.fontFamily}
          />
          <SemanticUnitView
            unit={unit}
            visual={visual}
            fontFamily={settings.fontFamily}
            fontScale={settings.fontScale}
            lineHeightScale={settings.lineHeightScale}
            reducedMotion={reducedMotion}
          />
          <ContextStack
            units={nextUnits}
            direction="below"
            layout={visual.layout}
            contextVisibility={visual.contextVisibility * 0.7}
            fontFamily={settings.fontFamily}
          />
        </div>
      </div>

      <ReaderControls visible={controlsVisible} />
    </div>
  );
}
