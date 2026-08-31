import type { SemanticUnit } from "../../models/SemanticUnit";
import type { ReaderLayout } from "../../models/VisualState";
import { FONT_OPTIONS, type FontFamilyId } from "../../styles/fonts";

type Props = {
  units: SemanticUnit[];
  direction: "above" | "below";
  layout: ReaderLayout;
  contextVisibility: number;
  fontFamily: FontFamilyId;
};

/**
 * Renders faint previous/next units so the reader keeps a sense of
 * continuity instead of the context disappearing every step (avoids the
 * classic word-by-word RSVP feeling).
 */
export function ContextStack({ units, direction, layout, contextVisibility, fontFamily }: Props) {
  if (layout === "isolated-concept" || units.length === 0) return null;

  const cssFamily = FONT_OPTIONS.find((f) => f.id === fontFamily)?.cssFamily ?? FONT_OPTIONS[0].cssFamily;
  const maxCount = layout === "flow-stack" ? 2 : 1;
  const visibleUnits = direction === "above" ? units.slice(-maxCount) : units.slice(0, maxCount);
  const ordered = direction === "above" ? visibleUnits : [...visibleUnits];

  return (
    <div className="context-stack" aria-hidden="true">
      {ordered.map((unit, i) => {
        const distanceFromCurrent = direction === "above" ? ordered.length - i : i + 1;
        const opacity = Math.max(0, contextVisibility * (1 - distanceFromCurrent * 0.32));
        const scale = 1 - distanceFromCurrent * 0.04;
        return (
          <p
            key={unit.id}
            className="context-unit"
            style={{
              fontFamily: cssFamily,
              opacity,
              transform: `scale(${scale})`,
            }}
          >
            {unit.text}
          </p>
        );
      })}
    </div>
  );
}
