import { DashboardShell } from "./features/dashboard/components/dashboard-shell";

function resolveApiBaseUrl() {
  return window.location.origin;
}

function resolveWebSocketUrl(apiBaseUrl: string) {
  const url = new URL("/ws/events", apiBaseUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

function App() {
  const apiBaseUrl = resolveApiBaseUrl();
  const websocketUrl = resolveWebSocketUrl(apiBaseUrl);

  return (
    <main>
      <DashboardShell apiBaseUrl={apiBaseUrl} websocketUrl={websocketUrl} />
    </main>
  );
}

export default App;
