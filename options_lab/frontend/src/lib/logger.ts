'use client';

/**
 * OptionsLab Client-Side Structured Logger & Error Interceptor
 * Intercepts unhandled errors, promise rejections, and streams logs to the backend.
 */

interface LogPayload {
  level: 'info' | 'warn' | 'error';
  message: string;
  source?: string;
  lineno?: number;
  colno?: number;
  stack?: string;
  url?: string;
  timestamp: string;
  data?: any;
}

export function initClientLogger() {
  if (typeof window === 'undefined') return;

  // Prevent multiple initializations
  if ((window as any).__OPTIONS_LAB_LOGGER_INIT__) return;
  (window as any).__OPTIONS_LAB_LOGGER_INIT__ = true;

  // Intercept Global Uncaught Errors
  window.addEventListener('error', (event) => {
    const errorLog: LogPayload = {
      level: 'error',
      message: event.message || 'Uncaught window error',
      source: event.filename || 'unknown',
      lineno: event.lineno,
      colno: event.colno,
      stack: event.error?.stack || '',
      url: window.location.href,
      timestamp: new Date().toISOString(),
    };

    console.warn('[OptionsLab Global Error Intercepted]:', errorLog);
    sendTelemetry(errorLog);
  });

  // Intercept Unhandled Promise Rejections
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason;
    const errorLog: LogPayload = {
      level: 'error',
      message: reason instanceof Error ? reason.message : String(reason),
      stack: reason instanceof Error ? reason.stack : '',
      url: window.location.href,
      timestamp: new Date().toISOString(),
      data: { type: 'UNHANDLED_PROMISE_REJECTION' }
    };

    console.warn('[OptionsLab Unhandled Promise Rejection Intercepted]:', errorLog);
    sendTelemetry(errorLog);
  });

  console.log('[OptionsLab Logger] Client telemetry and error interceptor initialized.');
}

async function sendTelemetry(payload: LogPayload) {
  try {
    await fetch('/api/logs/client-error', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    // Fail silently to prevent recursive logging
  }
}
