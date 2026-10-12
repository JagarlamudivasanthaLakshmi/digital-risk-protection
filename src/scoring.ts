import type { Brand, MonitoredItem } from "../db/schema";

export type RiskSignal = Record<string, string | number>;
export type RiskScore = {
  risk_score: number;
  severity: "low" | "medium" | "high" | "critical";
  signals: RiskSignal[];
  explanation: string;
};

const suspiciousTerms = ["urgent", "verify your account", "password", "claim reward", "suspended"];
const socialSources = new Set([
  "social", "instagram", "facebook", "x", "linkedin", "youtube", "tiktok",
]);

function normalizeName(value: string): string {
  return value
    .normalize("NFKD")
    .toLocaleLowerCase()
    .replace(/[0-9]/g, (character) => ({ "0": "o", "1": "l", "3": "e", "5": "s" })[character] ?? character)
    .replace(/[а]/g, "a")
    .replace(/[е]/g, "e")
    .replace(/[орсхі]/g, (character) => ({ о: "o", р: "p", с: "c", х: "x", і: "i" })[character] ?? character)
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]/g, "");
}

function longestMatch(
  left: string,
  right: string,
  leftStart: number,
  leftEnd: number,
  rightStart: number,
  rightEnd: number,
): [number, number, number] {
  let bestLeft = leftStart;
  let bestRight = rightStart;
  let bestSize = 0;
  let previous = new Map<number, number>();

  for (let leftIndex = leftStart; leftIndex < leftEnd; leftIndex += 1) {
    const current = new Map<number, number>();
    for (let rightIndex = rightStart; rightIndex < rightEnd; rightIndex += 1) {
      if (left[leftIndex] !== right[rightIndex]) continue;
      const size = (previous.get(rightIndex - 1) ?? 0) + 1;
      current.set(rightIndex, size);
      if (size > bestSize) {
        bestLeft = leftIndex - size + 1;
        bestRight = rightIndex - size + 1;
        bestSize = size;
      }
    }
    previous = current;
  }
  return [bestLeft, bestRight, bestSize];
}

function sequenceRatio(left: string, right: string): number {
  const matchingBlocks: number[] = [];
  const pending: Array<[number, number, number, number]> = [
    [0, left.length, 0, right.length],
  ];
  while (pending.length) {
    const [leftStart, leftEnd, rightStart, rightEnd] = pending.pop()!;
    const [matchLeft, matchRight, size] = longestMatch(
      left, right, leftStart, leftEnd, rightStart, rightEnd,
    );
    if (!size) continue;
    matchingBlocks.push(size);
    if (leftStart < matchLeft && rightStart < matchRight) {
      pending.push([leftStart, matchLeft, rightStart, matchRight]);
    }
    if (matchLeft + size < leftEnd && matchRight + size < rightEnd) {
      pending.push([matchLeft + size, leftEnd, matchRight + size, rightEnd]);
    }
  }
  const matching = matchingBlocks.reduce((sum, size) => sum + size, 0);
  return left.length + right.length ? (2 * matching) / (left.length + right.length) : 1;
}

function hostname(value: string): string {
  try {
    return new URL(value.includes("://") ? value : `https://${value}`).hostname
      .toLowerCase()
      .replace(/^www\./, "")
      .replace(/\.$/, "");
  } catch {
    return "";
  }
}

function isOfficialUrl(url: string, officialUrls: string[]): boolean {
  const candidate = hostname(url);
  if (!candidate) return false;
  let candidatePath = "";
  try {
    candidatePath = new URL(url).pathname.replace(/\/+$/, "").toLowerCase();
  } catch {
    return false;
  }
  return officialUrls.some((officialUrl) => {
    const officialHost = hostname(officialUrl);
    if (!officialHost || officialHost !== candidate) return false;
    try {
      const path = new URL(officialUrl.includes("://") ? officialUrl : `https://${officialUrl}`)
        .pathname.replace(/\/+$/, "").toLowerCase();
      return !path || path === candidatePath;
    } catch {
      return false;
    }
  });
}

export function isOfficialApp(
  item: {
    externalId?: string;
    url?: string;
    metadata?: Record<string, unknown>;
  },
  officialApps: string[],
): boolean {
  const ids = new Set([
    (item.externalId ?? "").toLowerCase(),
    String(item.metadata?.bundle_id ?? "").toLowerCase(),
    String(item.metadata?.store_id ?? "").toLowerCase(),
  ]);
  const url = (item.url ?? "").replace(/\/+$/, "").toLowerCase();
  return officialApps.some((entry) => {
    const value = entry.trim();
    if (!value) return false;
    const folded = value.toLowerCase().replace(/\/+$/, "");
    if (ids.has(folded) || folded === url) return true;
    return [...value.matchAll(/id(\d+)/gi)].some((match) => ids.has(match[1].toLowerCase()));
  });
}

function domainAllowed(url: string, domains: string[]): boolean {
  const host = hostname(url);
  return !!host && domains.some((domain) => {
    const allowed = hostname(domain);
    return !!allowed && (host === allowed || host.endsWith(`.${allowed}`));
  });
}

export function scoreItem(item: MonitoredItem, brand: Brand): RiskScore {
  if (socialSources.has(item.source) && item.url && isOfficialUrl(item.url, brand.officialSocialAccounts)) {
    return { risk_score: 0, severity: "low", signals: [], explanation: "Official social account is allowlisted." };
  }
  if (
    (item.source === "app_store" || item.source === "google_play")
    && isOfficialApp(item, brand.officialApps)
  ) {
    return { risk_score: 0, severity: "low", signals: [], explanation: "Official mobile application is allowlisted." };
  }
  if (item.url && domainAllowed(item.url, brand.officialDomains)) {
    return { risk_score: 0, severity: "low", signals: [], explanation: "URL is allowlisted." };
  }

  const signals: RiskSignal[] = [];
  const text = `${item.name} ${item.content}`.toLocaleLowerCase();
  for (const term of suspiciousTerms) {
    if (text.includes(term)) signals.push({ signal: "suspicious_language", term, weight: 15 });
  }

  const candidateDescription = `${item.name} ${item.content}`.toLocaleLowerCase().replace(/\s+/g, " ").trim();
  const officialDescription = brand.description.toLocaleLowerCase().replace(/\s+/g, " ").trim();
  if (candidateDescription.length >= 80 && officialDescription.length >= 80) {
    const similarity = sequenceRatio(
      candidateDescription.slice(0, 2000),
      officialDescription.slice(0, 2000),
    );
    if (similarity >= 0.82) {
      signals.push({ signal: "brand_description_similarity", similarity: Math.round(similarity * 100) / 100, weight: 20 });
    }
  }

  const similarity = sequenceRatio(normalizeName(item.name), normalizeName(brand.name));
  if (similarity >= 0.7 && similarity < 0.995) {
    signals.push({ signal: "similar_brand_name", similarity: Math.round(similarity * 100) / 100, weight: 25 });
  }

  const host = hostname(item.url);
  if (host && brand.officialDomains.length && !domainAllowed(item.url, brand.officialDomains)) {
    signals.push({ signal: "unofficial_domain", hostname: host, weight: 35 });
  }

  if (
    (item.source === "app_store" || item.source === "google_play")
    && item.publisher.trim()
    && brand.officialPublishers.length
    && !brand.officialPublishers.some(
      (publisher) => publisher.trim().toLocaleLowerCase() === item.publisher.trim().toLocaleLowerCase(),
    )
  ) {
    signals.push({ signal: "unverified_publisher", publisher: item.publisher.trim().toLocaleLowerCase(), weight: 20 });
  }

  const riskScore = Math.min(100, signals.reduce((sum, signal) => sum + Number(signal.weight ?? 0), 0));
  const severity = riskScore >= 80 ? "critical" : riskScore >= 55 ? "high" : riskScore >= 30 ? "medium" : "low";
  return {
    risk_score: riskScore,
    severity,
    signals,
    explanation: signals.length
      ? `Risk signals: ${signals.map((signal) => String(signal.signal).replaceAll("_", " ")).join(", ")}`
      : "No configured risk signals were detected.",
  };
}
