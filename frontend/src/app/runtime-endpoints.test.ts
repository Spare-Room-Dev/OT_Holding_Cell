import { describe, expect, it } from "vitest";

import { resolveRuntimeEndpoints } from "./runtime-endpoints";

describe("runtime endpoint resolution", () => {
  it("prefers explicit API and WS environment variables when provided", () => {
    const endpoints = resolveRuntimeEndpoints({
      env: {
        VITE_API_BASE_URL: "https://api.example.com/",
        VITE_WS_URL: "wss://stream.example.com/ws/events",
      },
      locationOrigin: "https://app.example.com",
    });

    expect(endpoints.apiBaseUrl).toBe("https://api.example.com");
    expect(endpoints.websocketUrl).toBe("wss://stream.example.com/ws/events");
  });

  it("falls back to legacy VITE_BACKEND_URL when API base URL is not set", () => {
    const endpoints = resolveRuntimeEndpoints({
      env: {
        VITE_BACKEND_URL: "https://legacy-api.example.com/",
      },
      locationOrigin: "https://app.example.com",
    });

    expect(endpoints.apiBaseUrl).toBe("https://legacy-api.example.com");
    expect(endpoints.websocketUrl).toBe("wss://legacy-api.example.com/ws/events");
  });

  it("falls back to same-origin URLs when no environment variables are provided", () => {
    const endpoints = resolveRuntimeEndpoints({
      env: {},
      locationOrigin: "https://app.example.com",
    });

    expect(endpoints.apiBaseUrl).toBe("https://app.example.com");
    expect(endpoints.websocketUrl).toBe("wss://app.example.com/ws/events");
  });

  it("derives insecure websocket protocol only for local http origins", () => {
    const endpoints = resolveRuntimeEndpoints({
      env: {},
      locationOrigin: "http://localhost:5173",
    });

    expect(endpoints.apiBaseUrl).toBe("http://localhost:5173");
    expect(endpoints.websocketUrl).toBe("ws://localhost:5173/ws/events");
  });
});
