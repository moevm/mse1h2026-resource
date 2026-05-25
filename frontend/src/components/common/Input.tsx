import React from 'react';
import type { InputHTMLAttributes, ReactNode } from 'react';

import { cn } from '../../lib/utils/cn';
import { FormField } from '../../shared/components/FormField';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
  icon?: ReactNode;
  wrapperClassName?: string;
}

export const Input: React.FC<InputProps> = ({
  label,
  hint,
  error,
  icon,
  className = '',
  wrapperClassName = '',
  id,
  ...rest
}) => {
  const inputId = id ?? label?.toLowerCase().replaceAll(' ', '-');

  return (
    <FormField label={label} hint={hint} error={error} icon={icon} wrapperClassName={wrapperClassName} id={inputId}>
      <input
        id={inputId}
        className={cn(
          'h-10 w-full rounded-lg border bg-slate-800/80 px-3.5 py-2 text-sm text-slate-200',
          'placeholder:text-slate-500',
          'transition-all duration-200',
          'hover:border-slate-600 hover:bg-slate-800',
          'focus:border-blue-500 focus:bg-slate-800 focus:ring-2 focus:ring-blue-500/40 focus:outline-none',
          'disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-slate-800/80',
          error ? 'border-red-500/60 bg-red-500/5 focus:border-red-500 focus:ring-red-500/40' : 'border-slate-700/80',
          icon && 'pl-10',
          className,
        )}
        {...rest}
      />
    </FormField>
  );
};
