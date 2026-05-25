import React from 'react';

import { IconExclamation } from '../../components/icons';

interface FormFieldProps {
  label?: string;
  hint?: string;
  error?: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  wrapperClassName?: string;
  id?: string;
}

export const FormField: React.FC<FormFieldProps> = ({ label, hint, error, icon, children, wrapperClassName = '', id }) => {
  const fieldId = id ?? label?.toLowerCase().replaceAll(' ', '-');

  return (
    <div className={wrapperClassName}>
      {label && (
        <label htmlFor={fieldId} className="mb-2 block text-sm font-medium text-slate-300">
          {label}
        </label>
      )}
      <div className="group relative">
        {icon && (
          <span className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-slate-500 transition-colors group-focus-within:text-slate-400">
            {icon}
          </span>
        )}
        {children}
      </div>
      {error && (
        <p className="mt-1.5 flex items-center gap-1 text-xs text-red-400">
          <IconExclamation className="h-3.5 w-3.5" />
          {error}
        </p>
      )}
      {hint && !error && <p className="mt-1.5 text-xs text-slate-500">{hint}</p>}
    </div>
  );
};
