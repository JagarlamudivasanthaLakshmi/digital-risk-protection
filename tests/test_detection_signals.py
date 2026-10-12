from io import BytesIO

from django.test import SimpleTestCase
from PIL import Image, ImageDraw

from detection.logo_similarity import logo_similarity
from detection.name_similarity import name_similarity
from detection.text_analyzer import analyze_text


class DetectionSignalTests(SimpleTestCase):
    def test_name_similarity_handles_spacing_diacritics_and_typos(self):
        self.assertEqual(name_similarity("Northstar-Bank", "northstar bank"), 1.0)
        self.assertEqual(name_similarity("Nórthstar Bank", "Northstar Bank"), 1.0)
        self.assertGreater(name_similarity("Northstarr Bank", "Northstar Bank"), 0.85)
        self.assertLess(name_similarity("Different Company", "Northstar Bank"), 0.6)

    def test_description_similarity_requires_substantial_matching_text(self):
        brand_description = (
            "Northstar Bank helps customers manage everyday spending, save for major "
            "life goals, and access secure digital banking support from our team."
        )
        signals = analyze_text(
            "Northstar Bank helps customers manage everyday spending, save for major "
            "life goals, and access secure digital banking support from our team.",
            official_description=brand_description,
        )
        self.assertEqual(signals[0]["signal"], "brand_description_similarity")

        unrelated = analyze_text(
            "A fun game with rewards and puzzles for friends.",
            official_description=brand_description,
        )
        self.assertEqual(unrelated, [])

    def test_logo_similarity_compares_local_images(self):
        original = Image.new("RGB", (64, 64), "white")
        drawing = ImageDraw.Draw(original)
        drawing.rectangle((12, 12, 50, 50), fill="black")
        identical = BytesIO()
        original.save(identical, format="PNG")

        self.assertEqual(
            logo_similarity(identical.getvalue(), identical.getvalue()),
            1.0,
        )
        self.assertIsNone(logo_similarity(None, identical.getvalue()))
