import { describe, expect, it } from "vitest";
import { maskSourceIp } from "./masking";

describe("maskSourceIp", () => {
  it("masks ipv4 addresses with public-safe defaults", () => {
    expect(maskSourceIp("203.0.113.42")).toBe("203.0.x.x");
  });
});
