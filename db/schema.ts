import { sql } from "drizzle-orm";
import {
  boolean,
  index,
  integer,
  jsonb,
  pgTable,
  serial,
  text,
  timestamp,
  uniqueIndex,
} from "drizzle-orm/pg-core";

export const brands = pgTable(
  "brands",
  {
    id: serial("id").primaryKey(),
    ownerId: text("owner_id").notNull(),
    name: text("name").notNull(),
    description: text("description").notNull().default(""),
    officialDomains: jsonb("official_domains").$type<string[]>().notNull().default([]),
    officialPublishers: jsonb("official_publishers").$type<string[]>().notNull().default([]),
    officialSocialAccounts: jsonb("official_social_accounts").$type<string[]>().notNull().default([]),
    officialApps: jsonb("official_apps").$type<string[]>().notNull().default([]),
    socialSearchEnabled: boolean("social_search_enabled").notNull().default(true),
    appStoreSearchEnabled: boolean("app_store_search_enabled").notNull().default(true),
    googlePlaySearchEnabled: boolean("google_play_search_enabled").notNull().default(true),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => ({
    ownerNameUnique: uniqueIndex("brands_owner_name_unique").on(table.ownerId, table.name),
    ownerIdx: index("brands_owner_idx").on(table.ownerId),
  }),
);

export const monitoredItems = pgTable(
  "monitored_items",
  {
    id: serial("id").primaryKey(),
    brandId: integer("brand_id").notNull().references(() => brands.id, { onDelete: "cascade" }),
    source: text("source").notNull(),
    externalId: text("external_id").notNull().default(""),
    name: text("name").notNull(),
    url: text("url").notNull().default(""),
    publisher: text("publisher").notNull().default(""),
    content: text("content").notNull().default(""),
    metadata: jsonb("metadata").$type<Record<string, unknown>>().notNull().default({}),
    lastSeenAt: timestamp("last_seen_at", { withTimezone: true }).notNull().defaultNow(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => ({
    brandSourceExternalUnique: uniqueIndex("monitored_items_brand_source_external_unique")
      .on(table.brandId, table.source, table.externalId)
      .where(sql`${table.externalId} <> ''`),
    brandIdx: index("monitored_items_brand_idx").on(table.brandId),
  }),
);

export const findings = pgTable(
  "findings",
  {
    id: serial("id").primaryKey(),
    brandId: integer("brand_id").notNull().references(() => brands.id, { onDelete: "cascade" }),
    monitoredItemId: integer("monitored_item_id").references(() => monitoredItems.id, {
      onDelete: "set null",
    }),
    riskScore: integer("risk_score").notNull().default(0),
    severity: text("severity").notNull().default("low"),
    signals: jsonb("signals").$type<Array<Record<string, unknown>>>().notNull().default([]),
    explanation: text("explanation").notNull().default(""),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => ({
    brandCreatedIdx: index("findings_brand_created_idx").on(table.brandId, table.createdAt),
    itemIdx: index("findings_item_idx").on(table.monitoredItemId),
  }),
);

export const alerts = pgTable(
  "alerts",
  {
    id: serial("id").primaryKey(),
    findingId: integer("finding_id").notNull().unique().references(() => findings.id, {
      onDelete: "cascade",
    }),
    status: text("status").notNull().default("open"),
    assignedTo: text("assigned_to"),
    notes: text("notes").notNull().default(""),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => ({
    statusCreatedIdx: index("alerts_status_created_idx").on(table.status, table.createdAt),
  }),
);

export type Brand = typeof brands.$inferSelect;
export type NewBrand = typeof brands.$inferInsert;
export type MonitoredItem = typeof monitoredItems.$inferSelect;
export type NewMonitoredItem = typeof monitoredItems.$inferInsert;
export type Finding = typeof findings.$inferSelect;
export type Alert = typeof alerts.$inferSelect;
