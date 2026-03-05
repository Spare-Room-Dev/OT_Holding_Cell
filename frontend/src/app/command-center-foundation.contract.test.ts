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

describe("command-center foundation contract", () => {
  it("loads global font and foundation style imports once at bootstrap", () => {
    const mainSource = readFileSync(mainPath, "utf8");

    expect(mainSource).toContain('import "@fontsource/vt323";');
    expect(mainSource).toContain('import "@fontsource/share-tech-mono";');
    expect(mainSource).toContain('import "./styles/command-center-foundation.css";');
  });

  it("attaches minimal shell class hooks in App", () => {
    const appSource = readFileSync(appPath, "utf8");

    expect(appSource).toContain('<main className="command-center-shell">');
    expect(appSource).toContain('className="command-center-shell__viewport"');
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
