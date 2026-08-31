type Props = {
  label: string;
  value: number;
  onChange: (value: number) => void;
};

export function VariableSlider({ label, value, onChange }: Props) {
  return (
    <div className="variable-slider">
      <label>
        <span>{label}</span>
        <span>{value.toFixed(2)}</span>
      </label>
      <input
        type="range"
        min={0}
        max={1}
        step={0.01}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}
