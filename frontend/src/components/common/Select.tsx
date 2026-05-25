import React from 'react';
import type { ReactNode, SelectHTMLAttributes } from 'react';

import { cn } from '../../lib/utils/cn';
import { FormField } from '../../shared/components/FormField';

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  hint?: string;
  error?: string;
  options: SelectOption[];
  placeholder?: string;
  wrapperClassName?: string;
  children?: ReactNode;
}

export const Select: React.FC<SelectProps> = ({
  label,
  hint,
  error,
  options,
  placeholder,
  className = '',
  wrapperClassName = '',
  id,
  children,
  ...rest
}) => {
  const selectId = id ?? label?.toLowerCase().replaceAll(' ', '-');

  return (
    <FormField label={label} hint={hint} error={error} wrapperClassName={wrapperClassName} id={selectId}>
      <div className="relative">
        <select
          id={selectId}
          className={cn(
            'h-10 w-full rounded-lg border bg-slate-800/80 px-3.5 py-2 pr-10 text-sm text-slate-200',
            'cursor-pointer transition-all duration-200',
            'hover:border-slate-600 hover:bg-slate-800',
            'focus:border-blue-500 focus:bg-slate-800 focus:ring-2 focus:ring-blue-500/40 focus:outline-none',
            'disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-slate-800/80',
            'appearance-none',
            error ? 'border-red-500/60 bg-red-500/5 focus:border-red-500 focus:ring-red-500/40' : 'border-slate-700/80',
            className,
          )}
          {...rest}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {children ??
            options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
        </select>
        <span className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-slate-500">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </span>
      </div>
    </FormField>
  );
};
