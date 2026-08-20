'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertOctagon, RefreshCw, Terminal, RotateCcw, Copy, Check } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  copied: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    copied: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
      copied: false,
    };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ error, errorInfo });
    console.error('[OptionsLab React ErrorBoundary Caught]:', error, errorInfo);

    // Transmit telemetry log to backend logger endpoint
    try {
      fetch('/api/logs/client-error', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'REACT_RENDER_ERROR',
          message: error.message || String(error),
          stack: error.stack || '',
          componentStack: errorInfo.componentStack || '',
          url: typeof window !== 'undefined' ? window.location.href : '',
          timestamp: new Date().toISOString(),
        }),
      }).catch((e) => console.warn('Failed to stream client log to backend:', e));
    } catch (e) {
      // no-op
    }
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  private handleFullReload = () => {
    if (typeof window !== 'undefined') {
      window.location.reload();
    }
  };

  private handleCopy = () => {
    const errorDetails = `[OptionsLab Error]\nMessage: ${this.state.error?.message}\nStack: ${this.state.error?.stack}\nComponent Stack: ${this.state.errorInfo?.componentStack}`;
    navigator.clipboard.writeText(errorDetails);
    this.setState({ copied: true });
    setTimeout(() => this.setState({ copied: false }), 2000);
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[450px] flex items-center justify-center p-6">
          <div className="max-w-2xl w-full velzon-card p-6 bg-white border border-rose-200 rounded-2xl shadow-xl space-y-5">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center border border-rose-100 flex-shrink-0">
                <AlertOctagon className="h-6 w-6" />
              </div>
              <div>
                <h2 className="text-base font-bold text-slate-800">Application Runtime Exception Caught</h2>
                <p className="text-xs text-slate-500">The ErrorBoundary safely isolated a client-side exception and logged it to the system console.</p>
              </div>
            </div>

            {/* Error Message Banner */}
            <div className="p-3 bg-rose-50/70 border border-rose-200 rounded-lg text-xs font-mono text-rose-800 break-words">
              <strong>Error:</strong> {this.state.error?.message || 'Unknown render exception'}
            </div>

            {/* Detailed Component Stack Trace */}
            {this.state.error?.stack && (
              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-[11px] font-bold text-slate-500">
                  <span className="flex items-center gap-1"><Terminal className="h-3.5 w-3.5" /> Stack Trace:</span>
                  <button
                    onClick={this.handleCopy}
                    className="flex items-center gap-1 text-indigo-600 hover:text-indigo-800 transition text-[10px]"
                  >
                    {this.state.copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    {this.state.copied ? 'Copied' : 'Copy Trace'}
                  </button>
                </div>
                <pre className="p-3 bg-slate-900 text-slate-200 text-[10px] font-mono rounded-lg overflow-x-auto max-h-48 leading-relaxed">
                  {this.state.error.stack}
                  {this.state.errorInfo?.componentStack && `\n\nComponent Hierarchy:${this.state.errorInfo.componentStack}`}
                </pre>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button
                onClick={this.handleReset}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-1.5 shadow-sm"
              >
                <RefreshCw className="h-3.5 w-3.5" /> Retry Component
              </button>
              <button
                onClick={this.handleFullReload}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold transition flex items-center gap-1.5"
              >
                <RotateCcw className="h-3.5 w-3.5" /> Reload Application
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
