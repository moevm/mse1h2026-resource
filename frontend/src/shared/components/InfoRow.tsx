import React from 'react';

interface InfoRowProps {
  label: string;
  value: string;
  warn?: boolean;
  icon?: React.ReactNode;
}

export const InfoRow: React.FC<InfoRowProps> = ({ label, value, warn, icon }) => {
  return (
    <div className="flex items-center justify-between py-0.5 text-sm">
      <span className="flex items-center gap-2 text-slate-400">
        {icon}
        {label}
      </span>
      <span className="font-mono font-medium" style={{ color: warn ? '#ef4444' : '#e2e8f0' }}>
        {value}
      </span>
    </div>
  );
};
