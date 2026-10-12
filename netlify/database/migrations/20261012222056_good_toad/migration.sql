CREATE TABLE "alerts" (
	"id" serial PRIMARY KEY,
	"finding_id" integer NOT NULL UNIQUE,
	"status" text DEFAULT 'open' NOT NULL,
	"assigned_to" text,
	"notes" text DEFAULT '' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "brands" (
	"id" serial PRIMARY KEY,
	"owner_id" text NOT NULL,
	"name" text NOT NULL,
	"description" text DEFAULT '' NOT NULL,
	"official_domains" jsonb DEFAULT '[]' NOT NULL,
	"official_publishers" jsonb DEFAULT '[]' NOT NULL,
	"official_social_accounts" jsonb DEFAULT '[]' NOT NULL,
	"official_apps" jsonb DEFAULT '[]' NOT NULL,
	"social_search_enabled" boolean DEFAULT true NOT NULL,
	"app_store_search_enabled" boolean DEFAULT true NOT NULL,
	"google_play_search_enabled" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "findings" (
	"id" serial PRIMARY KEY,
	"brand_id" integer NOT NULL,
	"monitored_item_id" integer,
	"risk_score" integer DEFAULT 0 NOT NULL,
	"severity" text DEFAULT 'low' NOT NULL,
	"signals" jsonb DEFAULT '[]' NOT NULL,
	"explanation" text DEFAULT '' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "monitored_items" (
	"id" serial PRIMARY KEY,
	"brand_id" integer NOT NULL,
	"source" text NOT NULL,
	"external_id" text DEFAULT '' NOT NULL,
	"name" text NOT NULL,
	"url" text DEFAULT '' NOT NULL,
	"publisher" text DEFAULT '' NOT NULL,
	"content" text DEFAULT '' NOT NULL,
	"metadata" jsonb DEFAULT '{}' NOT NULL,
	"last_seen_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE INDEX "alerts_status_created_idx" ON "alerts" ("status","created_at");--> statement-breakpoint
CREATE UNIQUE INDEX "brands_owner_name_unique" ON "brands" ("owner_id","name");--> statement-breakpoint
CREATE INDEX "brands_owner_idx" ON "brands" ("owner_id");--> statement-breakpoint
CREATE INDEX "findings_brand_created_idx" ON "findings" ("brand_id","created_at");--> statement-breakpoint
CREATE INDEX "findings_item_idx" ON "findings" ("monitored_item_id");--> statement-breakpoint
CREATE UNIQUE INDEX "monitored_items_brand_source_external_unique" ON "monitored_items" ("brand_id","source","external_id") WHERE "external_id" <> '';--> statement-breakpoint
CREATE INDEX "monitored_items_brand_idx" ON "monitored_items" ("brand_id");--> statement-breakpoint
ALTER TABLE "alerts" ADD CONSTRAINT "alerts_finding_id_findings_id_fkey" FOREIGN KEY ("finding_id") REFERENCES "findings"("id") ON DELETE CASCADE;--> statement-breakpoint
ALTER TABLE "findings" ADD CONSTRAINT "findings_brand_id_brands_id_fkey" FOREIGN KEY ("brand_id") REFERENCES "brands"("id") ON DELETE CASCADE;--> statement-breakpoint
ALTER TABLE "findings" ADD CONSTRAINT "findings_monitored_item_id_monitored_items_id_fkey" FOREIGN KEY ("monitored_item_id") REFERENCES "monitored_items"("id") ON DELETE SET NULL;--> statement-breakpoint
ALTER TABLE "monitored_items" ADD CONSTRAINT "monitored_items_brand_id_brands_id_fkey" FOREIGN KEY ("brand_id") REFERENCES "brands"("id") ON DELETE CASCADE;