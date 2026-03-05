import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const projectRoot = join(import.meta.dirname, "..", "..");
const mainPath = join(projectRoot, "src", "main.tsx");
const appPath = join(projectRoot, "src", "App.tsx");
const foundationPath = join(
  projectRoot,
  "src",
  "styles",
  "command-center-foundation.css",
);

function assertCommandCenterShellContract(source: string): void {
  if (!source.includes('<main className="command-center-shell">')) {
    throw new Error("Expected command-center-shell main hook.");
  }

  if (!source.includes('<div className="command-center-shell__viewport">')) {
    throw new Error("Expected command-center-shell__viewport hook.");
  }
}

describe("command-center foundation contract", () => {
  it("loads global font and foundation style imports once at bootstrap", () => {
    const mainSource = readFileSync(mainPath, "utf8");

    expect(mainSource).toContain('import "@fontsource/vt323";');
    expect(mainSource).toContain('import "@fontsource/share-tech-mono";');
    expect(mainSource).toContain('import "./styles/command-center-foundation.css";');
  });

  it("attaches minimal shell class hooks in App", () => {
    const appSource = readFileSync(appPath, "utf8");

    expect(() => assertCommandCenterShellContract(appSource)).not.toThrow();
  });

  it("accepts additive non-breaking root attributes with required shell hooks", () => {
    const appSource = `
      <main className="command-center-shell" data-command-center-root="shell">
        <div className="command-center-shell__viewport" data-command-center-root="viewport">
          <DashboardShell />
        </div>
      </main>
    `;

    expect(() => assertCommandCenterShellContract(appSource)).not.toThrow();
  });

  it("fails when required shell hooks are missing or renamed", () => {
    const appSource = `
      <main className="command-center-root">
        <div className="command-center-shell__view">
          <DashboardShell />
        </div>
      </main>
    `;

    expect(() => assertCommandCenterShellContract(appSource)).toThrow(
      /command-center-shell/,
    );
  });

  it("defines shell framing and typography lane utilities", () => {
    expect(existsSync(foundationPath)).toBe(true);

    const foundationSource = readFileSync(foundationPath, "utf8");

    expect(foundationSource).toContain(".command-center-shell");
    expect(foundationSource).toContain("background-image:");
    expect(foundationSource).toContain("var(--hc-grid-line)");
    expect(foundationSource).toContain(".cc-type-display");
    expect(foundationSource).toContain(".cc-type-data");
    expect(foundationSource).toContain("text-transform: uppercase;");
    expect(foundationSource).toContain("text-transform: none;");
  });
});
