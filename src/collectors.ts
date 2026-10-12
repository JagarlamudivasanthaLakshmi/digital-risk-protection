import gplay from "google-play-scraper";
import type { Brand } from "../db/schema";
import { isOfficialApp } from "./scoring";

export class CollectorError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CollectorError";
  }
}

type Candidate = {
  source: string;
  externalId: string;
  name: string;
  url: string;
  publisher: string;
  content: string;
  metadata: Record<string, unknown>;
};
type CollectionResult = { candidates: Candidate[]; warnings: string[] };

async function getJson(url: URL): Promise<Record<string, unknown>> {
  let response: Response;
  try {
    response = await fetch(url, {
      headers: { "user-agent": "DigitalRiskProtectionPrototype/1.0" },
      signal: AbortSignal.timeout(8000),
    });
  } catch (error) {
    throw new CollectorError(
      `The provider could not be reached (${error instanceof Error ? error.name : "network error"}).`,
    );
  }
  if (!response.ok) throw new CollectorError(`The provider returned HTTP ${response.status}.`);
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new CollectorError("The provider returned an invalid response.");
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new CollectorError("The provider response had an unexpected format.");
  }
  return payload as Record<string, unknown>;
}

function officialSocialUrl(url: string, officialUrls: string[]): boolean {
  let candidate: URL;
  try {
    candidate = new URL(url);
  } catch {
    return false;
  }
  const candidatePath = candidate.pathname.replace(/\/+$/, "").toLowerCase();
  return officialUrls.some((entry) => {
    try {
      const official = new URL(entry.includes("://") ? entry : `https://${entry}`);
      return official.hostname.toLowerCase().replace(/^www\./, "") === candidate.hostname.toLowerCase().replace(/^www\./, "")
        && (!official.pathname.replace(/\/+$/, "") || official.pathname.replace(/\/+$/, "").toLowerCase() === candidatePath);
    } catch {
      return false;
    }
  });
}

async function collectSocial(brand: Brand, limit: number): Promise<CollectionResult> {
  const results: Candidate[] = [];
  const errors: string[] = [];
  const blueskyUrl = new URL("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors");
  blueskyUrl.searchParams.set("q", brand.name);
  blueskyUrl.searchParams.set("limit", String(limit));
  try {
    const payload = await getJson(blueskyUrl);
    const actors = Array.isArray(payload.actors) ? payload.actors : [];
    for (const rawActor of actors) {
      if (!rawActor || typeof rawActor !== "object") continue;
      const actor = rawActor as Record<string, unknown>;
      if (typeof actor.handle !== "string" || typeof actor.did !== "string") continue;
      const profileUrl = `https://bsky.app/profile/${encodeURIComponent(actor.handle)}`;
      if (officialSocialUrl(profileUrl, brand.officialSocialAccounts)) continue;
      results.push({
        source: "social",
        externalId: `bluesky:${actor.did}`,
        name: String(actor.displayName || actor.handle).slice(0, 255),
        url: profileUrl,
        publisher: "Bluesky",
        content: String(actor.description || "").slice(0, 4000),
        metadata: {
          provider: "bluesky",
          handle: actor.handle,
          avatar: String(actor.avatar || ""),
          followers: actor.followersCount ?? null,
        },
      });
    }
  } catch (error) {
    errors.push(`Bluesky: ${error instanceof Error ? error.message : "provider error"}`);
  }

  const instances = (process.env.MASTODON_INSTANCES || "mastodon.social")
    .split(",")
    .map((instance) => instance.trim())
    .filter(Boolean);
  for (const instance of instances) {
    let base: URL;
    try {
      base = new URL(instance.includes("://") ? instance : `https://${instance}`);
    } catch {
      errors.push("Mastodon: configured instance URL is invalid.");
      continue;
    }
    if (base.protocol !== "https:") {
      errors.push("Mastodon: configured instances must use HTTPS.");
      continue;
    }
    const searchUrl = new URL("/api/v2/search", base);
    searchUrl.searchParams.set("q", brand.name);
    searchUrl.searchParams.set("type", "accounts");
    searchUrl.searchParams.set("limit", String(Math.min(limit, 40)));
    try {
      const payload = await getJson(searchUrl);
      const accounts = Array.isArray(payload.accounts) ? payload.accounts : [];
      for (const rawAccount of accounts) {
        if (!rawAccount || typeof rawAccount !== "object") continue;
        const account = rawAccount as Record<string, unknown>;
        if (typeof account.url !== "string" || account.id == null) continue;
        if (officialSocialUrl(account.url, brand.officialSocialAccounts)) continue;
        results.push({
          source: "social",
          externalId: `mastodon:${base.hostname}:${account.id}`,
          name: String(account.display_name || account.acct || "").slice(0, 255),
          url: account.url,
          publisher: "Mastodon",
          content: String(account.note || "").slice(0, 4000),
          metadata: {
            provider: "mastodon",
            instance: base.hostname,
            acct: String(account.acct || ""),
            followers: account.followers_count ?? null,
          },
        });
      }
    } catch (error) {
      errors.push(`${base.hostname}: ${error instanceof Error ? error.message : "provider error"}`);
    }
  }
  if (results.length === 0 && errors.length) throw new CollectorError(errors.join(" "));
  return { candidates: results.slice(0, limit), warnings: errors };
}

async function collectApple(brand: Brand, limit: number): Promise<CollectionResult> {
  const url = new URL("https://itunes.apple.com/search");
  url.searchParams.set("term", brand.name);
  url.searchParams.set("entity", "software");
  url.searchParams.set("country", (process.env.APPLE_APP_STORE_COUNTRY || "us").toLowerCase());
  url.searchParams.set("limit", String(limit));
  const payload = await getJson(url);
  const results = Array.isArray(payload.results) ? payload.results : [];
  const candidates = results.flatMap((rawApp) => {
    if (!rawApp || typeof rawApp !== "object") return [];
    const app = rawApp as Record<string, unknown>;
    if (app.trackId == null || typeof app.trackName !== "string") return [];
    const trackId = String(app.trackId);
    const item: Candidate = {
      source: "app_store",
      externalId: `apple:${trackId}`,
      name: app.trackName.slice(0, 255),
      url: String(app.trackViewUrl || ""),
      publisher: String(app.sellerName || "").slice(0, 255),
      content: String(app.description || "").slice(0, 4000),
      metadata: {
        provider: "apple_app_store",
        store_id: trackId,
        bundle_id: String(app.bundleId || ""),
        version: String(app.version || ""),
        price: String(app.formattedPrice || ""),
        artwork: String(app.artworkUrl100 || ""),
        genres: Array.isArray(app.genres) ? app.genres : [],
        average_rating: app.averageUserRating ?? null,
        rating_count: app.userRatingCount ?? null,
      },
    };
    return isOfficialApp(item, brand.officialApps) ? [] : [item];
  });
  return { candidates, warnings: [] };
}

async function collectGooglePlay(brand: Brand, limit: number): Promise<CollectionResult> {
  let searchResults: unknown;
  try {
    searchResults = await gplay.search({
      term: brand.name,
      num: limit,
      country: (process.env.GOOGLE_PLAY_COUNTRY || "us").toLowerCase(),
      lang: (process.env.GOOGLE_PLAY_LANGUAGE || "en").toLowerCase(),
    });
  } catch (error) {
    throw new CollectorError(
      `Google Play search failed: ${error instanceof Error ? error.message : "provider error"}`,
    );
  }
  if (!Array.isArray(searchResults)) {
    throw new CollectorError("Google Play returned an unexpected search response.");
  }
  const candidates = searchResults.flatMap((rawApp) => {
    if (!rawApp || typeof rawApp !== "object") return [];
    const app = rawApp as Record<string, unknown>;
    if (typeof app.appId !== "string" || typeof app.title !== "string") return [];
    const packageId = app.appId;
    const lang = process.env.GOOGLE_PLAY_LANGUAGE || "en";
    const country = process.env.GOOGLE_PLAY_COUNTRY || "us";
    const item: Candidate = {
      source: "google_play",
      externalId: `google_play:${packageId}`,
      name: app.title.slice(0, 255),
      url: `https://play.google.com/store/apps/details?id=${encodeURIComponent(packageId)}&hl=${encodeURIComponent(lang)}&gl=${encodeURIComponent(country)}`,
      publisher: String(app.developer || "").slice(0, 255),
      content: String(app.description || "").slice(0, 4000),
      metadata: {
        provider: "google_play",
        store_id: packageId,
        bundle_id: packageId,
        artwork: String(app.icon || ""),
        genre: String(app.genre || ""),
        score: app.score ?? null,
        installs: String(app.installs || ""),
        price: app.price ?? null,
      },
    };
    return isOfficialApp(item, brand.officialApps) ? [] : [item];
  });
  return { candidates, warnings: [] };
}

export async function collectCandidates(
  brand: Brand,
  source: string,
  limit = 20,
): Promise<CollectionResult> {
  const boundedLimit = Math.max(1, Math.min(Math.trunc(limit), 50));
  if (source === "social") {
    if (!brand.socialSearchEnabled) throw new CollectorError("Social monitoring is disabled for this brand.");
    return collectSocial(brand, boundedLimit);
  }
  if (source === "app_store") {
    if (!brand.appStoreSearchEnabled) throw new CollectorError("Apple App Store monitoring is disabled for this brand.");
    return collectApple(brand, boundedLimit);
  }
  if (source === "google_play") {
    if (!brand.googlePlaySearchEnabled) throw new CollectorError("Google Play monitoring is disabled for this brand.");
    return collectGooglePlay(brand, boundedLimit);
  }
  throw new CollectorError("Unsupported monitoring source.");
}
