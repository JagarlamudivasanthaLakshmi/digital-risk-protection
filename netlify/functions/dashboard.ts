import { desc, eq, inArray } from "drizzle-orm";
import { alerts, brands, findings, monitoredItems } from "../../db/schema";
import { currentUser, db, errorResponse, json } from "../utils/shared";

export default async function handler(request: Request): Promise<Response> {
  if (request.method !== "GET") return json({ error: "Method not allowed." }, 405);
  const user = await currentUser();
  if (!user) return json({ error: "Authentication required." }, 401);
  try {
    const ownedBrands = await db.select().from(brands).where(eq(brands.ownerId, user.id));
    const brandIds = ownedBrands.map((brand) => brand.id);
    if (!brandIds.length) {
      return json({
        brands: [],
        findings: [],
        alerts: [],
        stats: { brand_count: 0, detection_count: 0, social_detection_count: 0, app_detection_count: 0, open_alert_count: 0 },
      });
    }
    const [ownedFindings, ownedAlerts, items] = await Promise.all([
      db.select().from(findings).where(inArray(findings.brandId, brandIds)).orderBy(desc(findings.createdAt)).limit(100),
      db.select().from(alerts).innerJoin(findings, eq(alerts.findingId, findings.id))
        .where(inArray(findings.brandId, brandIds)).orderBy(desc(alerts.createdAt)).limit(100),
      db.select().from(monitoredItems).where(inArray(monitoredItems.brandId, brandIds)),
    ]);
    const itemById = new Map(items.map((item) => [item.id, item]));
    const alertByFinding = new Map(ownedAlerts.map(({ alerts: alert }) => [alert.findingId, alert]));
    const records = ownedFindings.map((finding) => ({
      ...finding,
      item: finding.monitoredItemId ? itemById.get(finding.monitoredItemId) ?? null : null,
      alert: alertByFinding.get(finding.id) ?? null,
    }));
    const socialIds = new Set(["social", "instagram", "facebook", "x", "linkedin", "youtube", "tiktok"]);
    const appIds = new Set(["app_store", "google_play"]);
    const findingItems = records.map((record) => record.item).filter(Boolean);
    return json({
      brands: ownedBrands,
      findings: records,
      alerts: ownedAlerts.map(({ alerts: alert, findings: finding }) => ({ ...alert, finding })),
      stats: {
        brand_count: ownedBrands.length,
        detection_count: ownedFindings.length,
        social_detection_count: findingItems.filter((item) => socialIds.has(item!.source)).length,
        app_detection_count: findingItems.filter((item) => appIds.has(item!.source)).length,
        open_alert_count: ownedAlerts.filter(({ alerts: alert }) => alert.status === "open").length,
      },
    });
  } catch (error) {
    return errorResponse(error);
  }
}
