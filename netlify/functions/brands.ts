import { and, asc, eq } from "drizzle-orm";
import { brands } from "../../db/schema";
import { currentUser, db, errorResponse, isStringList, json, sameOrigin } from "../utils/shared";

export default async function handler(request: Request): Promise<Response> {
  const user = await currentUser();
  if (!user) return json({ error: "Authentication required." }, 401);

  try {
    if (request.method === "GET") {
      const records = await db.select().from(brands)
        .where(eq(brands.ownerId, user.id))
        .orderBy(asc(brands.name));
      return json(records);
    }
    if (request.method !== "POST") {
      return json({ error: "Method not allowed." }, 405);
    }
    if (!sameOrigin(request)) return json({ error: "Cross-origin request rejected." }, 403);
    const body: unknown = await request.json();
    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return json({ error: "Request body must be a JSON object." }, 400);
    }
    const data = body as Record<string, unknown>;
    const name = typeof data.name === "string" ? data.name.trim() : "";
    if (!name || name.length > 160) return json({ error: "Brand name is required (maximum 160 characters)." }, 400);
    const listFields = [
      "officialDomains",
      "officialPublishers",
      "officialSocialAccounts",
      "officialApps",
    ] as const;
    for (const field of listFields) {
      if (data[field] !== undefined && !isStringList(data[field])) {
        return json({ error: `${field} must be a list of up to 100 text values.` }, 400);
      }
    }
    const existing = await db.select({ id: brands.id }).from(brands)
      .where(and(eq(brands.ownerId, user.id), eq(brands.name, name))).limit(1);
    if (existing.length) return json({ error: "A brand with that name already exists." }, 409);

    const [created] = await db.insert(brands).values({
      ownerId: user.id,
      name,
      description: typeof data.description === "string" ? data.description.slice(0, 10000) : "",
      officialDomains: isStringList(data.officialDomains) ? data.officialDomains.map((value) => value.trim()) : [],
      officialPublishers: isStringList(data.officialPublishers) ? data.officialPublishers.map((value) => value.trim()) : [],
      officialSocialAccounts: isStringList(data.officialSocialAccounts) ? data.officialSocialAccounts.map((value) => value.trim()) : [],
      officialApps: isStringList(data.officialApps) ? data.officialApps.map((value) => value.trim()) : [],
    }).returning();
    return json(created, 201);
  } catch (error) {
    return errorResponse(error);
  }
}
