import { DashboardShell } from "./features/dashboard/components/dashboard-shell";
import { resolveRuntimeEndpoints } from "./app/runtime-endpoints";

function App() {
  const { apiBaseUrl, websocketUrl } = resolveRuntimeEndpoints();

  return (
    <main className="command-center-shell" data-command-center-root="shell">
      <div className="command-center-shell__viewport" data-command-center-root="viewport">
        <DashboardShell apiBaseUrl={apiBaseUrl} websocketUrl={websocketUrl} />
      </div>
    </main>
  );
}

export default App;
