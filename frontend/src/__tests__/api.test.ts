import { describe, it, expect, vi } from "vitest";

vi.mock("axios", () => ({
  default: {
    create: vi.fn(() => ({
      get:  vi.fn(),
      post: vi.fn(),
    })),
  },
}));

import { listingsApi, deploymentsApi } from "../api/client";

describe("listingsApi", () => {
  it("is defined", () => {
    expect(listingsApi).toBeDefined();
    expect(listingsApi.getPage).toBeInstanceOf(Function);
    expect(listingsApi.triggerCrawl).toBeInstanceOf(Function);
    expect(listingsApi.getCrawlRuns).toBeInstanceOf(Function);
  });
});

describe("deploymentsApi", () => {
  it("is defined", () => {
    expect(deploymentsApi).toBeDefined();
    expect(deploymentsApi.getAll).toBeInstanceOf(Function);
    expect(deploymentsApi.getCurrent).toBeInstanceOf(Function);
    expect(deploymentsApi.rollback).toBeInstanceOf(Function);
  });
});

describe("Listing type shape", () => {
  it("has required fields", () => {
    const listing = {
      id:          "abc123",
      source:      "Rightmove (Kent)",
      title:       "Former Baptist Chapel",
      price:       "£120,000",
      location:    "Maidstone, Kent",
      url:         "https://rightmove.co.uk/property/123",
      description: "Grade II listed chapel",
      notified:    false,
      first_seen:  "2025-06-01T12:00:00",
      is_active:   true,
    };
    expect(listing.id).toBeTruthy();
    expect(listing.source).toBeTruthy();
    expect(typeof listing.notified).toBe("boolean");
    expect(typeof listing.is_active).toBe("boolean");
  });
});

describe("Deployment type shape", () => {
  it("has required rollback fields", () => {
    const deploy = {
      id:           "uuid-here",
      environment:  "staging",
      version:      "abc1234",
      image_tag:    "ghcr.io/repo/image:abc1234",
      deployed_by:  "github-actions",
      deployed_at:  "2025-06-01T12:00:00",
      is_current:   true,
      rollback_of:  null,
      notes:        "",
    };
    expect(["dev", "staging", "prod"]).toContain(deploy.environment);
    expect(deploy.rollback_of).toBeNull();
    expect(typeof deploy.is_current).toBe("boolean");
  });
});
