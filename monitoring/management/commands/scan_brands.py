from django.core.management.base import BaseCommand, CommandError

from brands.models import Brand
from monitoring.collectors.providers import CollectorError
from monitoring.models import MonitoredItem
from monitoring.services import scan_brand


SOURCES = (
    (MonitoredItem.Source.SOCIAL, "social_search_enabled"),
    (MonitoredItem.Source.APP_STORE, "app_store_search_enabled"),
    (MonitoredItem.Source.GOOGLE_PLAY, "google_play_search_enabled"),
)


class Command(BaseCommand):
    help = "Scan enabled social and app-store sources for every brand (for scheduled monitoring)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--brand-id",
            type=int,
            help="Scan only this brand ID instead of all brands.",
        )
        parser.add_argument(
            "--source",
            choices=[source for source, _ in SOURCES],
            help="Scan only this source.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Maximum candidates to request per source (1-50; default: 20).",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        if not 1 <= limit <= 50:
            raise CommandError("--limit must be between 1 and 50.")

        brands = Brand.objects.select_related("owner").order_by("pk")
        if options["brand_id"] is not None:
            brands = brands.filter(pk=options["brand_id"])
            if not brands.exists():
                raise CommandError(f"Brand {options['brand_id']} does not exist.")

        selected_source = options["source"]
        scanned = 0
        failures = []
        for brand in brands.iterator():
            for source, enabled_field in SOURCES:
                if selected_source and source != selected_source:
                    continue
                if not getattr(brand, enabled_field):
                    self.stdout.write(
                        f"Skipped {brand.name} ({source}): monitoring is disabled."
                    )
                    continue
                try:
                    result = scan_brand(brand, source, limit=limit)
                except CollectorError as exc:
                    message = f"{brand.name} ({source}): {exc}"
                    failures.append(message)
                    self.stderr.write(self.style.ERROR(f"Scan failed: {message}"))
                    continue

                scanned += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Scanned {brand.name} ({source}): "
                        f"{result['found']} found, {result['new']} new, "
                        f"{result['updated']} updated, {result['alerts']} alerts."
                    )
                )
                for warning in result["warnings"]:
                    self.stderr.write(self.style.WARNING(f"{brand.name} ({source}): {warning}"))

        self.stdout.write(f"Completed {scanned} scan(s).")
        if failures:
            raise CommandError(f"{len(failures)} scan(s) failed; see errors above.")
