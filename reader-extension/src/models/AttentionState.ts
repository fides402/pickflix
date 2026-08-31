export type AttentionState = {
  /** 0 -> 1, current estimated reader attention */
  estimatedAttention: number;
  /** 0 -> 1, accumulated tiredness */
  fatigue: number;
  /** 0 -> 1, moment-to-moment engagement */
  engagement: number;
};

export const DEFAULT_ATTENTION_STATE: AttentionState = {
  estimatedAttention: 0.75,
  fatigue: 0.2,
  engagement: 0.7,
};
