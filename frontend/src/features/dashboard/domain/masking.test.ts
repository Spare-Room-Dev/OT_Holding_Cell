import { describe, expect, it } from "vitest";
import { maskSourceIp } from "./masking";

describe("maskSourceIp", () => {
  it("masks ipv4 addresses with public-safe defaults", () => {
    expect(maskSourceIp("203.0.113.42")).toBe("203.0.x.x");
  });

  it("masks ipv6 addresses with public-safe defaults", () => {
    expect(maskSourceIp("2001:db8::1")).toBe("2001:db8:x:x:x:x:x:x");
  });

  it("supports configurable masking depth and token", () => {
    expect(
      maskSourceIp("203.0.113.42", {
        preserveIpv4Octets: 1,
        maskToken: "*",
      }),
    ).toBe("203.*.*.*");
  });

  it("returns generic masked token for invalid or empty input", () => {
    expect(maskSourceIp("not-an-ip")).toBe("[masked]");
    expect(maskSourceIp("   ")).toBe("[masked]");
  });
});
