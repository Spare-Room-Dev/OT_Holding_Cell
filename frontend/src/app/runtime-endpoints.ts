type RuntimeEnv = {
  VITE_API_BASE_URL?: string;
  VITE_BACKEND_URL?: string;
  VITE_WS_URL?: string;
};

export type RuntimeEndpoints = {
  apiBaseUrl: string;
  websocketUrl: string;
};

function normalizeUrl(url: string): string {
  return url.trim().replace(/\/+$/, "");
}

function firstConfiguredValue(values: Array<string | undefined>): string | null {
  for (const value of values) {
    if (value && value.trim().length > 0) {
      return value.trim();
    }
  }

  return null;
}

function deriveWebSocketUrl(apiBaseUrl: string): string {
  const url = new URL("/ws/events", `${normalizeUrl(apiBaseUrl)}/`);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export function resolveRuntimeEndpoints(options?: {
  env?: RuntimeEnv;
  locationOrigin?: string;
}): RuntimeEndpoints {
  const env = options?.env ?? (import.meta.env as RuntimeEnv);
  const locationOrigin = options?.locationOrigin ?? window.location.origin;

  const configuredApiBase = firstConfiguredValue([env.VITE_API_BASE_URL, env.VITE_BACKEND_URL]);
  const apiBaseUrl = normalizeUrl(configuredApiBase ?? locationOrigin);
  const configuredWebSocketUrl = firstConfiguredValue([env.VITE_WS_URL]);
  const websocketUrl = configuredWebSocketUrl
    ? normalizeUrl(configuredWebSocketUrl)
    : deriveWebSocketUrl(apiBaseUrl);

  return {
    apiBaseUrl,
    websocketUrl,
  };
}
