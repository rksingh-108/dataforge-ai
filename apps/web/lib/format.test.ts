import { describe, expect, it } from "vitest";

import { formatBytes, formatDateTime, formatDuration, titleCase } from "@/lib/format";

describe("formatBytes", () => {
  it("formats zero and invalid values", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(-1)).toBe("0 B");
  });

  it("formats kilobytes and megabytes", () => {
    expect(formatBytes(2048)).toBe("2 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5 MB");
  });
});

describe("formatDuration", () => {
  it("shows milliseconds under a second", () => {
    expect(formatDuration(450)).toBe("450 ms");
  });

  it("shows seconds above a second", () => {
    expect(formatDuration(2500)).toBe("2.5 s");
  });

  it("renders a dash for missing durations", () => {
    expect(formatDuration(0)).toBe("—");
  });
});

describe("titleCase", () => {
  it("humanises snake_case, dots and dashes", () => {
    expect(titleCase("analyst_query")).toBe("Analyst Query");
    expect(titleCase("datasource.created")).toBe("Datasource Created");
    expect(titleCase("read-only")).toBe("Read Only");
  });
});

describe("formatDateTime", () => {
  it("renders a dash for empty input", () => {
    expect(formatDateTime(null)).toBe("—");
    expect(formatDateTime("not-a-date")).toBe("—");
  });

  it("renders a formatted date for valid input", () => {
    expect(formatDateTime("2026-01-02T03:04:05Z")).not.toBe("—");
  });
});
