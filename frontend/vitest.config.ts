import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["toolchain.contract.test.ts"],
  },
});
