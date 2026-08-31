import { AnimatePresence, motion } from "framer-motion";
import type { SemanticUnit } from "../../models/SemanticUnit";
import type { VisualState } from "../../models/VisualState";
import { FONT_OPTIONS, type FontFamilyId } from "../../styles/fonts";

type Props = {
  unit: SemanticUnit;
  visual: VisualState;
  fontFamily: FontFamilyId;
  fontScale: number;
  lineHeightScale: number;
  reducedMotion: boolean;
};

export function SemanticUnitView({ unit, visual, fontFamily, fontScale, lineHeightScale, reducedMotion }: Props) {
  const cssFamily = FONT_OPTIONS.find((f) => f.id === fontFamily)?.cssFamily ?? FONT_OPTIONS[0].cssFamily;
  const motion_ = reducedMotion ? 0 : visual.motionAmount;
  const yOffset = visual.verticalPosition * 18;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={unit.id}
        className="unit-view"
        initial={{
          opacity: 0,
          y: yOffset + 14 * motion_,
          scale: 1 - 0.03 * motion_,
          filter: `contrast(${visual.contrast}) blur(${2 * motion_}px)`,
        }}
        animate={{
          opacity: visual.opacity,
          y: yOffset,
          scale: visual.chunkScale,
          filter: `contrast(${visual.contrast}) blur(0px)`,
        }}
        exit={{
          opacity: 0,
          y: yOffset - 10 * motion_,
          scale: 1 - 0.02 * motion_,
          filter: `contrast(${visual.contrast}) blur(${1.2 * motion_}px)`,
          transition: { duration: (reducedMotion ? 80 : visual.exitDuration) / 1000, ease: "easeInOut" },
        }}
        transition={{ duration: (reducedMotion ? 120 : visual.entranceDuration) / 1000, ease: "easeOut" }}
        style={{
          fontFamily: cssFamily,
          fontSize: `${visual.fontSize * fontScale}rem`,
          fontWeight: visual.fontWeight,
          lineHeight: visual.lineHeight * lineHeightScale,
          maxWidth: `${visual.maxWidth}ch`,
          letterSpacing: `${visual.letterSpacing}em`,
          padding: `${visual.surroundingWhitespace * 2.5}rem ${visual.surroundingWhitespace * 1.5}rem`,
        }}
      >
        {unit.text}
      </motion.div>
    </AnimatePresence>
  );
}
