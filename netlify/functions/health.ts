import { sql } from "drizzle-orm";
import { alerts, brands, findings, monitoredItems } from "../../db/schema";
import { db, json } from "../utils/shared";

export default async function handler(): Promise<Response> {
  try {
    await db.execute(sql`select 1`);
    await Promise.all([
      db.select({ id: brands.id }).from(brands).limit(0),
      db.select({ id: monitoredItems.id }).from(monitoredItems).limit(0),
      db.select({ id: findings.id }).from(findings).limit(0),
      db.select({ id: alerts.id }).from(alerts).limit(0),
    ]);
    return json({
      status: "ok",
      service: "digital-risk-protection-netlify",
      database: "connected",
      schema: "ready",
    });
  } catch (error) {
    console.error("Netlify Database health check failed:", error);
    return json({
      status: "error",
      service: "digital-risk-protection-netlify",
      database: "unavailable",
      schema: "not-ready",
      message: "Enable Netlify Database and apply the project migrations.",
    }, 503);
  }
}
