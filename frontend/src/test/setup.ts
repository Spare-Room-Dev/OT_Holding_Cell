import { afterEach, beforeEach, vi } from "vitest";

const reactActEnvironment = globalThis as typeof globalThis & {
  IS_REACT_ACT_ENVIRONMENT?: boolean;
};
reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;

beforeEach(() => {
  vi.useRealTimers();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllTimers();
});
