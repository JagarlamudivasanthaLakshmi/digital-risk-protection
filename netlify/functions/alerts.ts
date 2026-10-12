import { and, desc, eq, inArray } from "drizzle-orm";
import { alerts, brands, findings } from "../../db/schema";
import { currentUser, db, errorResponse, json, sameOrigin } from "../utils/shared";

const statuses = new Set(["open", "investigating", "resolved", "dismissed"]);

export default async function handler(request: Request): Promise<Response> {
  const user = await currentUser();
  if (!user) return json({ error: "Authentication required." }, 401);
  try {
    if (request.method === "GET") {
      const ownedBrands = await db.select({ id: brands.id }).from(brands)
        .where(eq(brands.ownerId, user.id));
      const ids = ownedBrands.map((brand) => brand.id);
      if (!ids.length) return json([]);
      const records = await db.select({ alert: alerts, finding: findings })
        .from(alerts).innerJoin(findings, eq(alerts.findingId, findings.id))
        .where(inArray(findings.brandId, ids)).orderBy(desc(alerts.createdAt)).limit(100);
      return json(records);
    }
    if (request.method !== "PATCH") return json({ error: "Method not allowed." }, 405);
    if (!sameOrigin(request)) return json({ error: "Cross-origin request rejected." }, 403);
    const body: unknown = await request.json();
    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return json({ error: "Request body must be a JSON object." }, 400);
    }
    const input = body as Record<string, unknown>;
    const alertId = Number(input.id);
    const status = typeof input.status === "string" ? input.status : "";
    if (!Number.isInteger(alertId) || alertId <= 0 || !statuses.has(status)) {
      return json({ error: "Provide a valid alert ID and status." }, 400);
    }
    const ownedBrands = await db.select({ id: brands.id }).from(brands)
      .where(eq(brands.ownerId, user.id));
    const ids = ownedBrands.map((brand) => brand.id);
    if (!ids.length) return json({ error: "Alert not found." }, 404);
    const [updated] = await db.update(alerts)
      .set({
        status,
        notes: typeof input.notes === "string" ? input.notes.slice(0, 10000) : "",
        updatedAt: new Date(),
      })
      .where(and(
        eq(alerts.id, alertId),
        inArray(alerts.findingId, db.select({ id: findings.id }).from(findings).where(inArray(findings.brandId, ids))),
      ))
      .returning();
    return updated ? json(updated) : json({ error: "Alert not found." }, 404);
  } catch (error) {
    return errorResponse(error);
  }
}
