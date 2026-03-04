import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const projectRoot = process.cwd();

function sourceAt(pathFromRoot: string): string {
  return readFileSync(resolve(projectRoot, pathFromRoot), "utf8");
}

describe("dashboard contract foundation", () => {
  it("includes typed REST and realtime contract modules", () => {
    const contractsPath = resolve(projectRoot, "src/features/dashboard/types/contracts.ts");
    const realtimePath = resolve(projectRoot, "src/features/dashboard/types/realtime.ts");

    expect(existsSync(contractsPath)).toBe(true);
    expect(existsSync(realtimePath)).toBe(true);

    const contractsSource = sourceAt("src/features/dashboard/types/contracts.ts");
    const realtimeSource = sourceAt("src/features/dashboard/types/realtime.ts");

    expect(contractsSource).toContain("DashboardPrisonerSummary");
    expect(contractsSource).toContain("DashboardPrisonerDetailResponse");
    expect(realtimeSource).toContain("RealtimeEventName");
    expect(realtimeSource).toContain("DashboardRealtimeEnvelope");
  });

  it("provides baseline dashboard style and test setup artifacts", () => {
    const tokensPath = resolve(projectRoot, "src/styles/tokens.css");
    const setupPath = resolve(projectRoot, "src/test/setup.ts");

    expect(existsSync(tokensPath)).toBe(true);
    expect(existsSync(setupPath)).toBe(true);

    const tokensSource = sourceAt("src/styles/tokens.css");
    const setupSource = sourceAt("src/test/setup.ts");

    expect(tokensSource).toContain("--hc-color-bg");
    expect(tokensSource).toContain("--hc-severity-critical");
    expect(setupSource).toContain("beforeEach");
    expect(setupSource).toContain("afterEach");
  });
});
