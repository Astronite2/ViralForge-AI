import { describe, expect, it } from "vitest";
import { formatName, pct, score } from "./format";

describe("intelligence formatting", () => {
  it("formats API enum values", () => expect(formatName("google_trends")).toBe("Google Trends"));
  it("normalizes fractional confidence", () => expect(pct(0.87)).toBe("87%"));
  it("retains percentage confidence", () => expect(pct(87)).toBe("87%"));
  it("formats missing scores safely", () => expect(score()).toBe("—"));
});
