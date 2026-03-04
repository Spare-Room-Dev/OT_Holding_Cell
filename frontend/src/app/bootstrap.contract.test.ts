import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("dashboard bootstrap contract", () => {
  it("mounts the app through a single AppProviders boundary", () => {
    const providersPath = resolve(process.cwd(), "src/app/providers.tsx");
    expect(existsSync(providersPath)).toBe(true);

    const mainSource = readFileSync(resolve(process.cwd(), "src/main.tsx"), "utf8");

    expect(mainSource).toContain('from "./app/providers"');
    expect(mainSource).toContain("<AppProviders>");
    expect(mainSource.match(/<AppProviders>/g)).toHaveLength(1);
    expect(mainSource).toContain("</AppProviders>");
  });
});
