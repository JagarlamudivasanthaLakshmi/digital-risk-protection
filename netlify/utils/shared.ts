import { getUser } from "@netlify/identity";
import { drizzle } from "drizzle-orm/netlify-db";
import * as schema from "../../db/schema";

export const db = drizzle({ schema });

export async function currentUser() {
  const user = await getUser();
  if (!user) return null;
  return { id: user.id, email: user.email };
}

export function json(data: unknown, status = 200): Response {
  return Response.json(data, {
    status,
    headers: { "cache-control": "no-store" },
  });
}

export function sameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  if (!origin) return true;
  try {
    return new URL(origin).origin === new URL(request.url).origin;
  } catch {
    return false;
  }
}

export function errorResponse(error: unknown): Response {
  const message = error instanceof Error ? error.message : "Unexpected server error.";
  console.error("Netlify function failed:", error);
  return json({ error: message }, 500);
}

export function isStringList(value: unknown): value is string[] {
  return Array.isArray(value)
    && value.length <= 100
    && value.every((entry) => typeof entry === "string" && entry.trim().length <= 1000);
}
