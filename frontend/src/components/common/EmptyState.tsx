import React from 'react';
import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ icon, title, description, action, className = '' }) => {
  return (
    <div
      className={`animate-fade-in flex flex-col items-center justify-center gap-4 px-8 py-16 text-center ${className}`}
    >
      {icon && <div className="rounded-2xl border border-slate-700/50 bg-slate-800/50 p-4 text-slate-500">{icon}</div>}
      <div className="space-y-2">
        <p className="text-base font-medium text-slate-300">{title}</p>
        {description && <p className="max-w-sm text-sm leading-relaxed text-slate-500">{description}</p>}
      </div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
};
