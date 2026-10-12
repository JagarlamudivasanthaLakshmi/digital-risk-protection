from unittest.mock import patch
from types import SimpleNamespace

from django.test import SimpleTestCase
import ssl

from brands.models import Brand
from .app_store_collector import collect_app_listings
from .google_play_collector import (
    _load_search_module,
    _search_google_play,
    collect_google_play_listings,
)
from .providers import CollectorError, official_app_matches, official_url_matches
from .social_collector import collect_social_mentions


class ProviderCollectorTests(SimpleTestCase):
    def setUp(self):
        self.brand = Brand(
            name="Northstar Bank",
            official_social_accounts=["https://bsky.app/profile/northstar.example"],
            official_apps=["com.northstar.bank", "12345"],
        )

    @patch("monitoring.collectors.social_collector.get_json")
    def test_social_search_normalizes_candidates_and_excludes_official_profile(self, get_json):
        get_json.side_effect = [
            {
                "actors": [
                    {
                        "did": "did:plc:official",
                        "handle": "northstar.example",
                        "displayName": "Northstar Bank",
                        "description": "Official profile",
                    },
                    {
                        "did": "did:plc:fake",
                        "handle": "northstar-help.bsky.social",
                        "displayName": "Northstar Bank Support",
                        "description": "Verify your account now",
                    },
                ]
            },
            {"accounts": []},
        ]

        candidates, warnings = collect_social_mentions(
            self.brand, mastodon_instances=["https://mastodon.example"]
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["external_id"], "bluesky:did:plc:fake")
        self.assertEqual(candidates[0]["metadata"]["provider"], "bluesky")
        self.assertEqual(warnings, [])
        self.assertEqual(get_json.call_count, 2)

    @patch("monitoring.collectors.social_collector.get_json")
    def test_social_search_returns_partial_results_and_provider_warning(self, get_json):
        get_json.side_effect = [
            CollectorError("Bluesky unavailable."),
            {"accounts": [{
                "id": "42",
                "acct": "northstar@mastodon.example",
                "display_name": "Northstar support",
                "url": "https://mastodon.example/@northstar",
                "note": "Support page",
            }]},
        ]

        candidates, warnings = collect_social_mentions(
            self.brand, mastodon_instances=["mastodon.example"]
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["external_id"], "mastodon:mastodon.example:42")
        self.assertEqual(len(warnings), 1)
        self.assertIn("Bluesky", warnings[0])

    @patch("monitoring.collectors.social_collector.get_json", side_effect=CollectorError("Unavailable."))
    def test_social_search_reports_when_all_providers_are_unavailable(self, get_json):
        with self.assertRaisesRegex(CollectorError, "Bluesky"):
            collect_social_mentions(
                self.brand, mastodon_instances=["mastodon.example"]
            )

    @patch("monitoring.collectors.app_store_collector.get_json")
    def test_app_store_search_maps_results_and_excludes_registered_app(self, get_json):
        get_json.return_value = {
            "results": [
                {
                    "trackId": 12345,
                    "trackName": "Northstar Bank",
                    "bundleId": "com.northstar.bank",
                    "sellerName": "Northstar Inc.",
                    "trackViewUrl": "https://apps.apple.com/app/id12345",
                    "description": "Official banking app.",
                    "artworkUrl100": "https://is1-ssl.mzstatic.com/image.png",
                },
                {
                    "trackId": 77777,
                    "trackName": "Northstar Bank Rewards",
                    "bundleId": "net.imposter.rewards",
                    "sellerName": "Unknown Games LLC",
                    "trackViewUrl": "https://apps.apple.com/app/id77777",
                    "description": "Claim a reward.",
                },
            ]
        }

        candidates, warnings = collect_app_listings(self.brand)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["external_id"], "apple:77777")
        self.assertEqual(candidates[0]["publisher"], "Unknown Games LLC")
        self.assertEqual(candidates[0]["metadata"]["bundle_id"], "net.imposter.rewards")
        self.assertEqual(warnings, [])

    @patch("monitoring.collectors.google_play_collector._search_google_play")
    def test_google_play_search_maps_results_and_excludes_registered_app(self, search):
        search.return_value = [
            {
                "appId": "com.northstar.bank",
                "title": "Northstar Bank",
                "developer": "Northstar Inc.",
                "description": "Official Android app.",
                "icon": "https://play-lh.googleusercontent.com/icon",
                "score": 4.5,
                "installs": "10,000+",
                "price": 0,
                "genre": "Finance",
            },
            {
                "appId": "net.imposter.rewards",
                "title": "Northstar Bank Rewards",
                "developer": "Unknown Games LLC",
                "description": "Claim a reward.",
            },
        ]

        candidates, warnings = collect_google_play_listings(self.brand)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["source"], "google_play")
        self.assertEqual(candidates[0]["external_id"], "google_play:net.imposter.rewards")
        self.assertEqual(candidates[0]["publisher"], "Unknown Games LLC")
        self.assertEqual(
            candidates[0]["metadata"]["bundle_id"],
            "net.imposter.rewards",
        )
        self.assertIn("play.google.com/store/apps/details", candidates[0]["url"])
        self.assertEqual(warnings, [])

    def test_google_play_search_import_restores_default_tls_verification(self):
        default_context_factory = ssl._create_default_https_context

        _load_search_module()

        self.assertIs(ssl._create_default_https_context, default_context_factory)

    @patch("monitoring.collectors.google_play_collector._load_search_module")
    def test_google_play_parser_failures_are_reported_as_provider_errors(self, load_module):
        module = SimpleNamespace(
            get=lambda url: "original getter",
            search=lambda *args, **kwargs: (_ for _ in ()).throw(KeyError("ds:4")),
        )
        load_module.return_value = module

        with self.assertRaisesRegex(CollectorError, "unexpected search response"):
            _search_google_play("Northstar", limit=5, country="us", lang="en")

        self.assertEqual(module.get("ignored"), "original getter")

    def test_official_asset_matchers_require_exact_profile_or_app_identity(self):
        self.assertTrue(official_url_matches(
            "https://bsky.app/profile/northstar.example",
            self.brand.official_social_accounts,
        ))
        self.assertFalse(official_url_matches(
            "https://bsky.app/profile/northstar-help.example",
            self.brand.official_social_accounts,
        ))
        self.assertTrue(official_app_matches(
            {
                "external_id": "apple:9999",
                "url": "https://apps.apple.com/app/id9999",
                "metadata": {"bundle_id": "com.other", "store_id": "9999"},
            },
            ["9999"],
        ))

    def test_official_app_matcher_ignores_malformed_legacy_values(self):
        self.assertFalse(
            official_app_matches(
                {
                    "external_id": "apple:77777",
                    "url": "https://apps.apple.com/app/id77777",
                    "metadata": {
                        "bundle_id": "net.imposter.app",
                        "store_id": "77777",
                    },
                },
                ["[][]google.com"],
            )
        )
