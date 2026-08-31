import { useReaderStore } from "../../store/readerStore";
import { ProgressBar } from "./ProgressBar";

const SPEEDS = [0.6, 0.8, 1, 1.25, 1.5, 2];

type Props = {
  visible: boolean;
};

export function ReaderControls({ visible }: Props) {
  const document = useReaderStore((s) => s.document);
  const currentIndex = useReaderStore((s) => s.currentIndex);
  const isPlaying = useReaderStore((s) => s.isPlaying);
  const speed = useReaderStore((s) => s.speedMultiplier);
  const togglePlay = useReaderStore((s) => s.togglePlay);
  const next = useReaderStore((s) => s.next);
  const previous = useReaderStore((s) => s.previous);
  const restart = useReaderStore((s) => s.restart);
  const setSpeed = useReaderStore((s) => s.setSpeed);
  const setCurrentIndex = useReaderStore((s) => s.setCurrentIndex);

  if (!document) return null;
  const total = document.units.length;

  return (
    <div className={`controls-bar${visible ? "" : " hidden"}`}>
      <div className="controls-row" style={{ gap: "0.6rem" }}>
        <ProgressBar current={currentIndex} total={total} />
        <span style={{ fontSize: "0.72rem", color: "var(--text-tertiary)", minWidth: "3.6rem", textAlign: "right" }}>
          {currentIndex + 1} / {total}
        </span>
      </div>
      <div className="controls-row">
        <button className="icon-button" title="Riparti dall'inizio (restart)" onClick={restart} aria-label="Riparti">
          ⟲
        </button>
        <button
          className="icon-button"
          title="Unità precedente (freccia sinistra)"
          onClick={previous}
          disabled={currentIndex === 0}
          aria-label="Precedente"
        >
          ‹
        </button>
        <button
          className="icon-button primary"
          title="Play/Pausa (spazio)"
          onClick={togglePlay}
          aria-label={isPlaying ? "Pausa" : "Play"}
        >
          {isPlaying ? "❚❚" : "▶"}
        </button>
        <button
          className="icon-button"
          title="Unità successiva (freccia destra)"
          onClick={next}
          disabled={currentIndex >= total - 1}
          aria-label="Successiva"
        >
          ›
        </button>

        <select
          className="speed-select"
          value={speed}
          onChange={(e) => setSpeed(Number(e.target.value))}
          aria-label="Velocità di lettura"
        >
          {SPEEDS.map((s) => (
            <option key={s} value={s}>
              {s}×
            </option>
          ))}
        </select>

        <input
          type="range"
          min={0}
          max={total - 1}
          value={currentIndex}
          onChange={(e) => setCurrentIndex(Number(e.target.value))}
          style={{ flex: 1 }}
          aria-label="Vai a un punto della lettura"
        />
      </div>
    </div>
  );
}
