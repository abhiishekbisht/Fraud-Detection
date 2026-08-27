/**
 * Session management utility for FraudLens frontend.
 * Manages unique per-browser session ID and custom fetch wrapper with X-Session-ID header.
 */

const SESSION_KEY = 'fraudlens_session_id';

export function getSessionId(): string {
  let sessionId = sessionStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = typeof crypto !== 'undefined' && crypto.randomUUID 
      ? crypto.randomUUID() 
      : 'sess_' + Math.random().toString(36).substring(2, 11) + Date.now().toString(36);
    sessionStorage.setItem(SESSION_KEY, sessionId);
  }
  return sessionId;
}

export function getSessionHeaders(extraHeaders: Record<string, string> = {}): Record<string, string> {
  return {
    'X-Session-ID': getSessionId(),
    ...extraHeaders,
  };
}

export async function fetchWithSession(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = getSessionHeaders((options.headers as Record<string, string>) || {});
  return fetch(url, {
    ...options,
    headers,
  });
}

export async function resetSessionData(): Promise<void> {
  const sessionId = getSessionId();
  try {
    await fetch('/api/reset', {
      method: 'POST',
      headers: {
        'X-Session-ID': sessionId,
      },
    });
  } catch (e) {
    console.error('Failed to reset session on server:', e);
  }
  sessionStorage.removeItem(SESSION_KEY);
  getSessionId();
}
