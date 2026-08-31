import type { ReadingRegime } from "./ReadingRegime";

export type ReaderLayout = "center-focus" | "flow-stack" | "isolated-concept";

export type VisualState = {
  regime: ReadingRegime;
  layout: ReaderLayout;

  /** rem */
  fontSize: number;
  fontWeight: number;
  lineHeight: number;

  /** ch, approximate reading column width */
  maxWidth: number;

  opacity: number;
  contrast: number;

  /** em */
  letterSpacing: number;

  /** -1 (up) -> 1 (down), compositional vertical bias */
  verticalPosition: number;

  /** ms */
  entranceDuration: number;
  /** ms, how long the unit stays fully readable before it may start fading */
  holdDuration: number;
  /** ms */
  exitDuration: number;

  /** 0 -> 1, how much translate/scale motion is used in transitions */
  motionAmount: number;

  /** 0 -> 1, how visible previous/next context units are */
  contextVisibility: number;

  /** 0 -> 1, extra whitespace multiplier around the current unit */
  surroundingWhitespace: number;

  /** relative scale applied to the current unit, 1 = neutral */
  chunkScale: number;
};
