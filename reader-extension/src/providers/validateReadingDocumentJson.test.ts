import { describe, expect, it } from "vitest";
import { validateReadingDocumentJson } from "./validateReadingDocumentJson";

function validUnit(overrides: Record<string, unknown> = {}) {
  return {
    id: "1",
    text: "Una unità di prova.",
    importance: 0.5,
    complexity: 0.5,
    intensity: 0.5,
    novelty: 0.5,
    emotion: 0.5,
    connectivity: 0.5,
    narrativity: 0.5,
    density: 0.5,
    ...overrides,
  };
}

function validDoc(units: unknown[] = [validUnit()]) {
  return JSON.stringify({ title: "Titolo di prova", author: "Autore", units });
}

describe("validateReadingDocumentJson", () => {
  it("accepts a well-formed document", () => {
    const result = validateReadingDocumentJson(validDoc());
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.document.title).toBe("Titolo di prova");
      expect(result.document.units).toHaveLength(1);
      expect(result.document.hasSemanticScores).toBe(true);
    }
  });

  it("rejects invalid JSON syntax with a readable error", () => {
    const result = validateReadingDocumentJson("{ not valid json");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors[0]).toMatch(/JSON valido/);
  });

  it("rejects a document missing 'title'", () => {
    const result = validateReadingDocumentJson(JSON.stringify({ units: [validUnit()] }));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors.some((e) => e.includes("title"))).toBe(true);
  });

  it("rejects a document with an empty units array", () => {
    const result = validateReadingDocumentJson(validDoc([]));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors.some((e) => e.includes("units"))).toBe(true);
  });

  it("rejects a unit missing a required scalar field", () => {
    const unit = validUnit();
    delete (unit as Record<string, unknown>).complexity;
    const result = validateReadingDocumentJson(validDoc([unit]));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors.some((e) => e.includes("complexity"))).toBe(true);
  });

  it("rejects a unit with a scalar value out of the 0-1 range", () => {
    const result = validateReadingDocumentJson(validDoc([validUnit({ importance: 1.5 })]));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors.some((e) => e.includes("importance"))).toBe(true);
  });

  it("rejects duplicate unit ids", () => {
    const result = validateReadingDocumentJson(validDoc([validUnit({ id: "1" }), validUnit({ id: "1" })]));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors.some((e) => e.includes("duplicato"))).toBe(true);
  });

  it("accepts boundary values 0 and 1 for scalar fields", () => {
    const zero = validUnit({
      id: "zero",
      importance: 0,
      complexity: 0,
      intensity: 0,
      novelty: 0,
      emotion: 0,
      connectivity: 0,
      narrativity: 0,
      density: 0,
    });
    const one = validUnit({
      id: "one",
      importance: 1,
      complexity: 1,
      intensity: 1,
      novelty: 1,
      emotion: 1,
      connectivity: 1,
      narrativity: 1,
      density: 1,
    });
    const result = validateReadingDocumentJson(validDoc([zero, one]));
    expect(result.ok).toBe(true);
  });

  it("rejects a root value that is an array instead of an object", () => {
    const result = validateReadingDocumentJson(JSON.stringify([validUnit()]));
    expect(result.ok).toBe(false);
  });
});
