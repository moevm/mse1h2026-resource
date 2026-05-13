import React from 'react';

import { getStatusColor } from '../../utils/colors';

interface StatusDotProps {
  status?: string;
  showLabel?: boolean;
  pulse?: boolean;
  size?: 'sm' | 'md';
}

export const StatusDot: React.FC<StatusDotProps> = ({ status, showLabel = false, pulse = false, size = 'sm' }) => {
  const color = getStatusColor(status);
  const label = status ?? 'unknown';
  const dotSize = size === 'sm' ? 'h-2 w-2' : 'h-2.5 w-2.5';

  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`inline-block ${dotSize} shrink-0 rounded-full ${pulse && status === 'active' ? 'animate-pulse' : ''}`}
        style={{ backgroundColor: color }}
      />
      {showLabel && (
        <span className="text-[11px] font-medium capitalize" style={{ color }}>
          {label}
        </span>
      )}
    </div>
  );
};