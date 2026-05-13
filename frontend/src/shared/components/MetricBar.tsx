import React from 'react';

interface MetricBarProps {
  label: string;
  value: number;
  max: number;
  unit: string;
  decimals?: number;
  colorMode?: 'auto' | 'always-green';
}

export const MetricBar: React.FC<MetricBarProps> = ({ label, value, max, unit, decimals = 0, colorMode = 'auto' }) => {
  const pct = Math.min(100, (value / max) * 100);

  let color = '#22c55e';
  if (colorMode === 'auto') {
    if (pct > 80) color = '#ef4444';
    else if (pct > 60) color = '#f59e0b';
  }

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm">
        <span className="text-slate-400">{label}</span>
        <span className="font-mono font-medium text-slate-200">
          {value.toFixed(decimals)} {unit}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-800/80">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
};
