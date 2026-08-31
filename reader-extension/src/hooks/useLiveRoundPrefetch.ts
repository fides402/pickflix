import { useEffect, useRef } from "react";
import { useReaderStore } from "../store/readerStore";
import { getLiveSession } from "../providers/liveSessionManager";

const PREFETCH_REMAINING_THRESHOLD = 5;

/**
 * When a ChatGPT live session is active, requests the next round in the
 * background once the reader is within a few units of the end of the
 * currently-loaded buffer — so, per the product request, the next round is
 * "già pronto" (already ready) shortly before the current one runs out.
 */
export function useLiveRoundPrefetch() {
  const document = useReaderStore((s) => s.document);
  const currentIndex = useReaderStore((s) => s.currentIndex);
  const liveSession = useReaderStore((s) => s.liveSession);
  const appendUnits = useReaderStore((s) => s.appendUnits);
  const setLiveSessionStatus = useReaderStore((s) => s.setLiveSessionStatus);
  const inFlightRef = useRef(false);

  useEffect(() => {
    if (!document || !liveSession.active || liveSession.generating || !liveSession.hasMore) return;
    if (inFlightRef.current) return;

    const remaining = document.units.length - 1 - currentIndex;
    if (remaining > PREFETCH_REMAINING_THRESHOLD) return;

    const session = getLiveSession();
    if (!session) return;

    inFlightRef.current = true;
    setLiveSessionStatus({ generating: true, error: null });

    session
      .requestNextRound()
      .then((units) => {
        appendUnits(units);
        const progress = session.progress;
        setLiveSessionStatus({
          generating: false,
          hasMore: session.hasMoreRounds,
          roundsDone: progress.doneRounds,
          roundsTotal: progress.totalRounds,
        });
      })
      .catch((err: unknown) => {
        setLiveSessionStatus({
          generating: false,
          error: err instanceof Error ? err.message : String(err),
        });
      })
      .finally(() => {
        inFlightRef.current = false;
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    document,
    currentIndex,
    liveSession.active,
    liveSession.generating,
    liveSession.hasMore,
    appendUnits,
    setLiveSessionStatus,
  ]);
}
