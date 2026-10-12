import { and, desc, eq } from "drizzle-orm";
import { alerts, brands, findings, monitoredItems } from "../../db/schema";
import { collectCandidates, CollectorError } from "../../src/collectors";
import { scoreItem } from "../../src/scoring";
import { currentUser, db, errorResponse, json, sameOrigin } from "../utils/shared";

const validSources = new Set(["social", "app_store", "google_play"]);

export default async function handler(request: Request): Promise<Response> {
  if (request.method !== "POST") return json({ error: "Method not allowed." }, 405);
  if (!sameOrigin(request)) return json({ error: "Cross-origin request rejected." }, 403);
  const user = await currentUser();
  if (!user) return json({ error: "Authentication required." }, 401);

  try {
    const body: unknown = await request.json();
    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return json({ error: "Request body must be a JSON object." }, 400);
    }
    const input = body as Record<string, unknown>;
    const brandId = Number(input.brandId);
    const source = typeof input.source === "string" ? input.source : "";
    const limit = Number(input.limit ?? 20);
    if (!Number.isInteger(brandId) || brandId <= 0 || !validSources.has(source)) {
      return json({ error: "Choose a valid brand and monitoring source." }, 400);
    }
    if (!Number.isInteger(limit) || limit < 1 || limit > 50) {
      return json({ error: "Scan limit must be from 1 to 50." }, 400);
    }
    const [brand] = await db.select().from(brands)
      .where(and(eq(brands.id, brandId), eq(brands.ownerId, user.id))).limit(1);
    if (!brand) return json({ error: "Brand not found." }, 404);

    let collection: Awaited<ReturnType<typeof collectCandidates>>;
    try {
      collection = await collectCandidates(brand, source, limit);
    } catch (error) {
      if (error instanceof CollectorError) return json({ error: error.message }, 502);
      throw error;
    }

    const { candidates, warnings } = collection;
    let newCount = 0;
    let alertCount = 0;
    for (const candidate of candidates) {
      const [previous] = await db.select().from(monitoredItems)
        .where(and(
          eq(monitoredItems.brandId, brand.id),
          eq(monitoredItems.source, candidate.source),
          eq(monitoredItems.externalId, candidate.externalId),
        )).limit(1);
      const [item] = previous
        ? await db.update(monitoredItems).set({ ...candidate, lastSeenAt: new Date() })
          .where(eq(monitoredItems.id, previous.id)).returning()
        : await db.insert(monitoredItems).values({ ...candidate, brandId: brand.id }).returning();
      if (!previous) newCount += 1;

      const score = scoreItem(item, brand);
      const [existingFinding] = await db.select().from(findings)
        .where(and(eq(findings.brandId, brand.id), eq(findings.monitoredItemId, item.id)))
        .orderBy(desc(findings.createdAt)).limit(1);
      const [finding] = existingFinding
        ? await db.update(findings).set({
          riskScore: score.risk_score,
          severity: score.severity,
          signals: score.signals,
          explanation: score.explanation,
        }).where(eq(findings.id, existingFinding.id)).returning()
        : await db.insert(findings).values({
          brandId: brand.id,
          monitoredItemId: item.id,
          riskScore: score.risk_score,
          severity: score.severity,
          signals: score.signals,
          explanation: score.explanation,
        }).returning();
      if (score.risk_score >= 30) {
        const [existingAlert] = await db.select({ id: alerts.id }).from(alerts)
          .where(eq(alerts.findingId, finding.id)).limit(1);
        if (!existingAlert) {
          await db.insert(alerts).values({ findingId: finding.id });
          alertCount += 1;
        }
      }
    }
    return json({
      found: candidates.length,
      new: newCount,
      updated: candidates.length - newCount,
      scored: candidates.length,
      alerts: alertCount,
      warnings,
    });
  } catch (error) {
    return errorResponse(error);
  }
}
