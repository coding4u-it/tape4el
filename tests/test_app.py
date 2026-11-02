import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as webapp


class WebApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        webapp.app.config.update(TESTING=True)
        cls.client = webapp.app.test_client()

    def test_home_lists_periodic_table(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Tavola periodica degli elementi", response.data)
        self.assertIn(b"Idrogeno", response.data)
        self.assertIn(b"Oganesio", response.data)
        self.assertEqual(response.data.count(b'class="element-tile"'), 120)

    def test_element_detail_and_missing_element(self):
        response = self.client.get("/element/8")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Ossigeno", response.data)
        self.assertEqual(self.client.get("/element/999").status_code, 404)

    def test_calculator_supports_nested_groups_and_hydrates(self):
        response = self.client.post("/calculator", data={"formula": "Ca(OH)2"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"74.09474 g/mol", response.data)
        hydrate = self.client.post(
            "/calculator", data={"formula": "CuSO₄·5H₂O"}
        )
        self.assertEqual(hydrate.status_code, 200)
        self.assertIn(b"Massa molare", hydrate.data)
        bracketed = self.client.post("/calculator", data={"formula": "Mg[OH]2"})
        self.assertEqual(bracketed.status_code, 200)
        self.assertNotIn(b"class=\"alert alert-error\"", bracketed.data)

    def test_calculator_rejects_invalid_formula(self):
        response = self.client.post("/calculator", data={"formula": "H2Xx"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Elemento chimico sconosciuto", response.data)

    def test_compounds_are_filtered_and_paginated(self):
        response = self.client.get("/compounds?kind=binario&element=H")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Composti inorganici", response.data)
        self.assertIn(b"Successiva", response.data)
        filtered = self.client.get("/compounds?kind=binario&element=H&category=2")
        self.assertEqual(filtered.status_code, 200)

    def test_about_and_existing_assets(self):
        self.assertEqual(self.client.get("/about").status_code, 200)
        with self.client.get("/assets/imgEl/8.jpg") as response:
            self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
