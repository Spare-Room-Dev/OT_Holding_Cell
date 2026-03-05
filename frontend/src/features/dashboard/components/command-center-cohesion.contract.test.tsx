import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const frontendRoot = join(import.meta.dirname, "..", "..", "..", "..");
const repositoryRoot = join(frontendRoot, "..");

const shellPath = join(frontendRoot, "src", "features", "dashboard", "components", "dashboard-shell.tsx");
const statsBarPath = join(frontendRoot, "src", "features", "dashboard", "components", "stats-bar.tsx");
const filterBarPath = join(frontendRoot, "src", "features", "dashboard", "components", "filter-bar.tsx");
const prisonerListPath = join(frontendRoot, "src", "features", "dashboard", "components", "prisoner-list.tsx");
const prisonerRowPath = join(frontendRoot, "src", "features", "dashboard", "components", "prisoner-row.tsx");
const detailPanePath = join(frontendRoot, "src", "features", "dashboard", "components", "detail-pane.tsx");
const responsiveSpecPath = join(frontendRoot, "e2e", "dashboard-responsive.spec.ts");
const dashboardOpsPath = join(repositoryRoot, "docs", "ops", "dashboard-ui.md");

describe("command-center cohesion contract", () => {
  it("keeps required cohesion hooks wired across all primary regions", () => {
    const shell = readFileSync(shellPath, "utf8");
    const statsBar = readFileSync(statsBarPath, "utf8");
    const filterBar = readFileSync(filterBarPath, "utf8");
    const prisonerList = readFileSync(prisonerListPath, "utf8");
    const prisonerRow = readFileSync(prisonerRowPath, "utf8");
    const detailPane = readFileSync(detailPanePath, "utf8");

    expect(shell).toContain('data-command-center-region="command-band"');
    expect(shell).toContain("dashboard-shell__top-strip");
    expect(shell).toContain("dashboard-shell__main-band");
    expect(shell).toContain("dashboard-shell__history-band");
    expect(shell).toContain("dashboard-shell__main-primary");
    expect(shell).toContain("dashboard-shell__main-detail");
    expect(shell).toContain('data-command-center-region="live-hero"');
    expect(shell).toContain('data-command-center-region="cell-view"');
    expect(shell).toContain('data-command-center-heading="shell-title"');
    expect(statsBar).toContain('data-command-center-region="kpi-band"');
    expect(filterBar).toContain('data-command-center-region="filter-band"');
    expect(prisonerList).toContain('data-command-center-region="live-list"');
    expect(prisonerList).toContain('data-command-center-heading="panel-title"');
    expect(prisonerRow).toContain('data-command-center-region="live-row"');
    expect(detailPane).toContain('data-command-center-region="dossier-pane"');
    expect(detailPane).toContain('data-command-center-heading="panel-title"');
  });

  it("requires responsive e2e coverage for cohesion hooks and zoom readability", () => {
    const responsiveSpec = readFileSync(responsiveSpecPath, "utf8");

    expect(responsiveSpec).toContain(".dashboard-shell__top-strip");
    expect(responsiveSpec).toContain(".dashboard-shell__main-band");
    expect(responsiveSpec).toContain(".dashboard-shell__history-band");
    expect(responsiveSpec).toContain('[data-command-center-region="live-hero"]');
    expect(responsiveSpec).toContain('[data-command-center-region="command-band"]');
    expect(responsiveSpec).toContain('[data-command-center-region="cell-view"]');
    expect(responsiveSpec).toContain('[data-command-center-region="kpi-band"]');
    expect(responsiveSpec).toContain('[data-command-center-region="filter-band"]');
    expect(responsiveSpec).toContain("assertNoWhiteBackdropExposure");
    expect(responsiveSpec).toContain("assertFrameContainmentContracts");
    expect(responsiveSpec).toContain("90%");
    expect(responsiveSpec).toContain("110%");
  });

  it("requires runbook evidence capture for desktop/mobile cohesion and zoom checks", () => {
    const dashboardOps = readFileSync(dashboardOpsPath, "utf8");

    expect(dashboardOps).toContain("Attach screenshot evidence");
    expect(dashboardOps).toContain("approved mockup");
    expect(dashboardOps).toContain("2/3 + 1/3");
    expect(dashboardOps).toContain("Live Breach History");
    expect(dashboardOps).toContain("cell-view parity");
    expect(dashboardOps).toContain("scroll attachment");
    expect(dashboardOps).toContain("frame containment");
    expect(dashboardOps).toContain("desktop command-center cohesion");
    expect(dashboardOps).toContain("mobile command-center cohesion");
    expect(dashboardOps).toContain("90%");
    expect(dashboardOps).toContain("110%");
  });
});
