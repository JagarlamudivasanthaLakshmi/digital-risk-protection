from django.test import SimpleTestCase

from detection.allowlist import is_allowlisted


class AllowlistTests(SimpleTestCase):
    def test_matches_hostname_and_subdomain(self):
        self.assertTrue(is_allowlisted("https://shop.example.com/path", ["example.com"]))
        self.assertFalse(is_allowlisted("https://notexample.com", ["example.com"]))
