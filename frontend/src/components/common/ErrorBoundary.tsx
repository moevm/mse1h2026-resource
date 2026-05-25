import { Component, type ErrorInfo, type ReactNode } from 'react';

import { Button } from './Button';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  override state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  override render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="flex h-screen flex-col items-center justify-center bg-slate-950 p-8 text-center">
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-red-500/10">
              <svg
                className="h-8 w-8 text-red-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                />
              </svg>
            </div>
            <h1 className="mb-2 text-xl font-semibold text-slate-100">Something went wrong</h1>
            <p className="mb-6 max-w-md text-sm text-slate-500">
              {this.state.error?.message ?? 'An unexpected error occurred while rendering this page.'}
            </p>
            <div className="flex gap-3">
              <Button variant="primary" size="sm" onClick={this.handleReset}>
                Try Again
              </Button>
              <Button variant="ghost" size="sm" onClick={() => window.location.reload()}>
                Reload Page
              </Button>
            </div>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
