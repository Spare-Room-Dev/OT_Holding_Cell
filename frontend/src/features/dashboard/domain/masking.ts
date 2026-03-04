export interface MaskSourceIpOptions {
  preserveIpv4Octets?: number;
  preserveIpv6Hextets?: number;
  maskToken?: string;
}

const DEFAULT_OPTIONS: Required<MaskSourceIpOptions> = {
  preserveIpv4Octets: 2,
  preserveIpv6Hextets: 2,
  maskToken: "x",
};

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function parseIpv4(ip: string): number[] | null {
  const parts = ip.split(".");
  if (parts.length !== 4) {
    return null;
  }

  const octets: number[] = [];
  for (const part of parts) {
    if (!/^\d+$/.test(part)) {
      return null;
    }

    const value = Number(part);
    if (!Number.isInteger(value) || value < 0 || value > 255) {
      return null;
    }
    octets.push(value);
  }

  return octets;
}

function expandIpv6(ip: string): string[] | null {
  const withoutZone = ip.split("%")[0];
  const lowered = withoutZone.toLowerCase();

  if (lowered.includes(":::")) {
    return null;
  }

  const parts = lowered.split("::");
  if (parts.length > 2) {
    return null;
  }

  const parseSide = (side: string): string[] => {
    if (side === "") {
      return [];
    }
    return side.split(":");
  };

  const left = parseSide(parts[0] ?? "");
  const right = parseSide(parts[1] ?? "");

  const all = [...left, ...right];
  if (all.some((segment) => !/^[0-9a-f]{1,4}$/.test(segment))) {
    return null;
  }

  if (parts.length === 1) {
    if (left.length !== 8) {
      return null;
    }
    return left;
  }

  const missingCount = 8 - (left.length + right.length);
  if (missingCount < 1) {
    return null;
  }

  return [...left, ...Array(missingCount).fill("0"), ...right];
}

function maskIpv4(ip: string, options: Required<MaskSourceIpOptions>): string | null {
  const octets = parseIpv4(ip);
  if (octets === null) {
    return null;
  }

  const preserveCount = clamp(options.preserveIpv4Octets, 0, 4);
  const masked = octets.map((octet, index) => (index < preserveCount ? String(octet) : options.maskToken));
  return masked.join(".");
}

function maskIpv6(ip: string, options: Required<MaskSourceIpOptions>): string | null {
  const hextets = expandIpv6(ip);
  if (hextets === null) {
    return null;
  }

  const preserveCount = clamp(options.preserveIpv6Hextets, 0, 8);
  return hextets.map((segment, index) => (index < preserveCount ? segment : options.maskToken)).join(":");
}

export function maskSourceIp(sourceIp: string, options: MaskSourceIpOptions = {}): string {
  const normalized = sourceIp.trim();
  if (normalized === "") {
    return "[masked]";
  }

  const mergedOptions: Required<MaskSourceIpOptions> = {
    preserveIpv4Octets: options.preserveIpv4Octets ?? DEFAULT_OPTIONS.preserveIpv4Octets,
    preserveIpv6Hextets: options.preserveIpv6Hextets ?? DEFAULT_OPTIONS.preserveIpv6Hextets,
    maskToken: options.maskToken ?? DEFAULT_OPTIONS.maskToken,
  };

  const maskedIpv4 = maskIpv4(normalized, mergedOptions);
  if (maskedIpv4 !== null) {
    return maskedIpv4;
  }

  const maskedIpv6 = maskIpv6(normalized, mergedOptions);
  if (maskedIpv6 !== null) {
    return maskedIpv6;
  }

  return "[masked]";
}
