import React from 'react';

export const LogoMark: React.FC = () => {
  return (
    <div
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-xs font-extrabold tracking-tight text-white shadow-lg shadow-blue-900/50 select-none"
      style={{ backgroundImage: 'linear-gradient(to bottom right, #3b82f6, #1d4ed8)' }}
    >
      RG
    </div>
  );
};
