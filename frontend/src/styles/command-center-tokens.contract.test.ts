import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const projectRoot = join(import.meta.dirname, "..", "..");
const tokensPath = join(projectRoot, "src", "styles", "tokens.css");
const shellChromePath = join(
  projectRoot,
  "src",
  "features",
  "dashboard",
  "components",
  "dashboard-shell-chrome.css",
);
const surfacePanelsPath = join(
  projectRoot,
  "src",
  "features",
  "dashboard",
  "components",
  "dashboard-surface-panels.css",
);
const packageJsonPath = join(projectRoot, "package.json");

describe("command-center token contract", () => {
  it("defines command-center shell, glow, spacing, and typography tokens", () => {
    const tokens = readFileSync(tokensPath, "utf8");

    const requiredTokens = [
      "--hc-shell-bg",
      "--hc-grid-line",
      "--hc-panel-outline",
      "--hc-glow-soft",
      "--hc-glow-strong",
      "--hc-space-5",
      "--hc-space-8",
      "--hc-font-display",
      "--hc-font-data",
      "--hc-font-value",
      "--hc-line-ui",
      "--hc-line-data",
      "--hc-tracking-ui",
      "--hc-frame-border-default",
      "--hc-frame-border-strong",
      "--hc-frame-bg-base",
      "--hc-frame-grid-overlay",
      "--hc-frame-heading-size",
      "--hc-frame-heading-spacing",
    ];

    for (const token of requiredTokens) {
      expect(tokens).toContain(token);
    }
  });

  it("keeps existing severity and connection identities unchanged", () => {
    const tokens = readFileSync(tokensPath, "utf8");

    expect(tokens).toContain("--hc-severity-low: #2e9f74;");
    expect(tokens).toContain("--hc-severity-caution: #f3c96a;");
    expect(tokens).toContain("--hc-severity-high: #f08d49;");
    expect(tokens).toContain("--hc-severity-critical: #db5f5f;");
    expect(tokens).toContain("--hc-connection-live: #4ac57a;");
    expect(tokens).toContain("--hc-connection-reconnecting: #f3c96a;");
    expect(tokens).toContain("--hc-connection-offline: #db5f5f;");
  });

  it("uses shared frame border, background, and heading primitives across shell and surface panel styles", () => {
    const shellChrome = readFileSync(shellChromePath, "utf8");
    const surfacePanels = readFileSync(surfacePanelsPath, "utf8");

    const requiredFramePrimitives = [
      "var(--hc-frame-border-default)",
      "var(--hc-frame-border-strong)",
      "var(--hc-frame-bg-base)",
      "var(--hc-frame-heading-size)",
      "var(--hc-frame-heading-spacing)",
    ];

    for (const framePrimitive of requiredFramePrimitives) {
      expect(shellChrome).toContain(framePrimitive);
      expect(surfacePanels).toContain(framePrimitive);
    }
  });

  it("pins approved font packages in frontend dependencies", () => {
    const packageJson = JSON.parse(readFileSync(packageJsonPath, "utf8")) as {
      dependencies?: Record<string, string>;
    };
    const dependencies = packageJson.dependencies ?? {};

    expect(dependencies["@fontsource/vt323"]).toBe("5.2.7");
    expect(dependencies["@fontsource/share-tech-mono"]).toBe("5.2.7");
  });
});
