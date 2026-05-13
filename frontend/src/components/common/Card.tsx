import React from 'react';
import type { ReactNode } from 'react';

interface CardProps {
  title?: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  noPadding?: boolean;
  interactive?: boolean;
}

export const Card: React.FC<CardProps> = ({
  title,
  description,
  action,
  children,
  className = '',
  noPadding = false,
  interactive = false,
}) => {
  const hasMeta = title != null || description != null || action != null;

  return (
    <div
      className={[
        'overflow-hidden rounded-xl border border-slate-800/80 bg-slate-900/80',
        'shadow-lg shadow-slate-950/50',
        interactive && 'cursor-pointer transition-all duration-200 hover:border-slate-700/80 hover:bg-slate-900',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {hasMeta && (
        <div className="flex items-start justify-between gap-4 border-b border-slate-800/60 px-5 pt-4 pb-3">
          <div className="min-w-0">
            {title && <h2 className="text-sm leading-snug font-semibold text-slate-100">{title}</h2>}
            {description && <p className="mt-1 text-xs text-slate-400">{description}</p>}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}
      <div className={noPadding ? '' : 'p-5'}>{children}</div>
    </div>
  );
};

interface SectionProps {
  title: string;
  children: ReactNode;
  className?: string;
}

export const Section: React.FC<SectionProps> = ({ title, children, className = '' }) => {
  return (
    <div className={className}>
      <h4 className="mb-3 text-xs font-semibold tracking-wide text-slate-400 uppercase">{title}</h4>
      {children}
    </div>
  );
};
