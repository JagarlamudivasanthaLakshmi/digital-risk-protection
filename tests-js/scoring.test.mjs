import test from "node:test";
import assert from "node:assert/strict";
import { scoreItem } from "../src/scoring.ts";

const brand = {
  name: "Northstar Bank",
  description: "A trusted financial service for personal and business accounts, offering reliable banking tools and support for customers around the world.",
  officialDomains: ["northstar.example"],
  officialPublishers: ["Northstar Inc."],
  officialSocialAccounts: ["https://bsky.app/profile/northstar.example"],
  officialApps: ["com.northstar.bank", "12345"],
};

function item(overrides = {}) {
  return {
    source: "social",
    externalId: "candidate-1",
    name: "Northstar Bank Support",
    url: "https://northstar-help.example/profile",
    publisher: "",
    content: "Verify your account now",
    metadata: {},
    ...overrides,
  };
}

test("suspicious social copy and a lookalike domain produce weighted signals", () => {
  const result = scoreItem(item(), brand);
  assert.equal(result.risk_score, 75);
  assert.equal(result.severity, "high");
  assert.deepEqual(result.signals.map((signal) => signal.signal), [
    "suspicious_language",
    "similar_brand_name",
    "unofficial_domain",
  ]);
});

test("official social profiles are allowlisted", () => {
  const result = scoreItem(item({
    name: "Northstar Bank",
    url: "https://bsky.app/profile/northstar.example",
    content: "",
  }), brand);
  assert.equal(result.risk_score, 0);
  assert.match(result.explanation, /Official social account/);
});

test("registered app IDs are allowlisted", () => {
  const result = scoreItem(item({
    source: "app_store",
    name: "Northstar Bank",
    externalId: "apple:555",
    url: "https://apps.apple.com/app/id555",
    content: "",
    metadata: { bundle_id: "com.northstar.bank", store_id: "555" },
  }), brand);
  assert.equal(result.risk_score, 0);
  assert.match(result.explanation, /Official mobile application/);
});

test("unverified app publishers and copied descriptions are scored", () => {
  const result = scoreItem(item({
    source: "google_play",
    name: "Northstar Bank",
    url: "https://play.google.com/store/apps/details?id=net.fake.app",
    publisher: "Unknown Publisher",
    content: brand.description,
  }), brand);
  assert.equal(result.severity, "high");
  assert.ok(result.signals.some((signal) => signal.signal === "unverified_publisher"));
  assert.ok(result.signals.some((signal) => signal.signal === "brand_description_similarity"));
});
