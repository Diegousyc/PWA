import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from http.server import ThreadingHTTPServer

from server import make_handler


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.data_file = Path(self.temporary_directory.name) / "products.json"
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            make_handler(self.data_file, Path(__file__).resolve().parents[1]),
        )
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self.connection = HTTPConnection("127.0.0.1", self.server.server_port)

    def tearDown(self):
        self.connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join()
        self.temporary_directory.cleanup()

    def request_json(self, method, body=None):
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if encoded else {}
        self.connection.request(method, "/api/products", body=encoded, headers=headers)
        response = self.connection.getresponse()
        payload = json.loads(response.read())
        return response.status, payload

    def test_get_returns_an_empty_catalog(self):
        status, payload = self.request_json("GET")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"products": []})

    def test_post_persists_product_and_replaces_duplicate_id(self):
        product = {
            "id": 123,
            "name": "Bocina portátil",
            "price": 649,
            "category": "Electrónica",
            "description": "Música para acompañarte.",
            "emoji": "🔊",
        }
        status, payload = self.request_json("POST", product)
        self.assertEqual(status, 200)
        self.assertEqual(payload["product"], product)

        updated_product = {**product, "price": 699}
        self.assertEqual(self.request_json("POST", updated_product)[0], 200)
        status, payload = self.request_json("GET")
        self.assertEqual(status, 200)
        self.assertEqual(payload["products"], [updated_product])

    def test_post_rejects_invalid_product(self):
        status, payload = self.request_json("POST", {"id": 1, "name": "", "price": -1})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)
        self.assertFalse(self.data_file.exists())

    def test_post_rejects_price_outside_finite_range(self):
        product = {
            "id": 1,
            "name": "Producto",
            "price": 10**400,
            "category": "Hogar",
            "description": "Precio fuera de rango.",
            "emoji": "📦",
        }
        status, payload = self.request_json("POST", product)
        self.assertEqual(status, 400)
        self.assertIn("error", payload)
        self.assertFalse(self.data_file.exists())


if __name__ == "__main__":
    unittest.main()
