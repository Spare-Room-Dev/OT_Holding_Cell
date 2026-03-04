import { DashboardShell } from "./features/dashboard/components/dashboard-shell";
import { resolveRuntimeEndpoints } from "./app/runtime-endpoints";

function App() {
  const { apiBaseUrl, websocketUrl } = resolveRuntimeEndpoints();

  return (
    <main>
      <DashboardShell apiBaseUrl={apiBaseUrl} websocketUrl={websocketUrl} />
    </main>
  );
}

export default App;
