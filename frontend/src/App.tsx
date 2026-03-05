import { DashboardShell } from "./features/dashboard/components/dashboard-shell";
import { resolveRuntimeEndpoints } from "./app/runtime-endpoints";

function App() {
  const { apiBaseUrl, websocketUrl } = resolveRuntimeEndpoints();

  return (
    <main className="command-center-shell">
      <div className="command-center-shell__viewport">
        <DashboardShell apiBaseUrl={apiBaseUrl} websocketUrl={websocketUrl} />
      </div>
    </main>
  );
}

export default App;
