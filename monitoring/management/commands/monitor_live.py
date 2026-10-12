import time

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Continuously poll enabled monitoring sources and update dashboard findings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=900,
            help="Seconds between scan cycles (minimum 60; default: 900).",
        )
        parser.add_argument("--brand-id", type=int, help="Monitor only this brand ID.")
        parser.add_argument(
            "--source",
            choices=("social", "app_store", "google_play"),
            help="Monitor only this source.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Maximum candidates per source scan (1-50; default: 20).",
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        if interval < 60:
            raise CommandError("--interval must be at least 60 seconds.")
        if not 1 <= options["limit"] <= 50:
            raise CommandError("--limit must be between 1 and 50.")

        self.stdout.write(self.style.SUCCESS(
            f"Live polling started; scan interval is {interval} seconds. Press Ctrl+C to stop."
        ))
        while True:
            started = time.monotonic()
            try:
                call_options = {"limit": options["limit"], "verbosity": 1}
                if options["brand_id"] is not None:
                    call_options["brand_id"] = options["brand_id"]
                if options["source"]:
                    call_options["source"] = options["source"]
                call_command("scan_brands", stdout=self.stdout, stderr=self.stderr, **call_options)
            except CommandError as exc:
                self.stderr.write(self.style.WARNING(
                    f"This polling cycle had scan failures; the next cycle will continue: {exc}"
                ))

            wait_for = max(0, interval - (time.monotonic() - started))
            self.stdout.write(f"Next scan cycle in {int(wait_for)} seconds.")
            try:
                time.sleep(wait_for)
            except KeyboardInterrupt:
                self.stdout.write(self.style.SUCCESS("Live polling stopped."))
                return
