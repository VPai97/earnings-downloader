import csv
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from api.app import app
from api.routes import companies as companies_module
from core.storage.bse_scrip import BseScripStore


class TestCompanySuggest(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", newline="", delete=False)
        writer = csv.writer(self.temp_file)
        writer.writerow(["Company name", "symbol", "ISIN"])
        writer.writerow(["ABB Ltd.", "ABB", "INE117A01022"])
        writer.writerow(["Aegis Logistics Ltd.", "AEGISLOG", "INE208C01025"])
        self.temp_file.close()

        companies_module.BSE_SCRIP_STORE = BseScripStore(self.temp_file.name)
        self.client = TestClient(app)

    def tearDown(self):
        os.unlink(self.temp_file.name)

    def test_suggest_prefix(self):
        response = self.client.get("/api/companies/suggest", params={"q": "AB", "region": "india"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        labels = [item["label"] for item in data]
        self.assertIn("ABB Ltd. (ABB)", labels)

    def test_suggest_symbol_prefix(self):
        response = self.client.get("/api/companies/suggest", params={"q": "AEGIS", "region": "india"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        labels = [item["label"] for item in data]
        self.assertIn("Aegis Logistics Ltd. (AEGISLOG)", labels)


if __name__ == "__main__":
    unittest.main()
