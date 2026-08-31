type Props = {
  current: number;
  total: number;
};

export function ProgressBar({ current, total }: Props) {
  const pct = total > 1 ? (current / (total - 1)) * 100 : 0;
  return (
    <div className="progress-bar-track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct)}>
      <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
    </div>
  );
}
