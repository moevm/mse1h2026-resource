import { StrictMode } from 'react';

import { QueryClientProvider } from '@tanstack/react-query';

import { createRoot } from 'react-dom/client';

import App from './App';
import './index.css';
import { queryClient } from './lib/queryClient';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
