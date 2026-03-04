import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("frontend toolchain contract", () => {
  it("defines deterministic scripts and required config files", () => {
    const packagePath = resolve(process.cwd(), "package.json");
    const packageJson = JSON.parse(readFileSync(packagePath, "utf8")) as {
      scripts?: Record<string, string>;
    };

    expect(packageJson.scripts).toMatchObject({
      dev: "vite",
      build: "tsc -b && vite build",
      test: "vitest",
    });

    const requiredFiles = [
      "index.html",
      "tsconfig.json",
      "tsconfig.node.json",
      "vite.config.ts",
    ];

    for (const file of requiredFiles) {
      expect(existsSync(resolve(process.cwd(), file))).toBe(true);
    }
  });
});
