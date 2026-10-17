import json
import math
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "server-data" / "products.json"
ALLOWED_CATEGORIES = {"Electrónica", "Accesorios", "Hogar", "Deportes"}


def validate_product(value):
    if not isinstance(value, dict):
        return None
    product_id = value.get("id")
    name = value.get("name")
    price = value.get("price")
    category = value.get("category")
    description = value.get("description")
    emoji = value.get("emoji")
    if isinstance(product_id, bool) or not isinstance(product_id, int) or product_id <= 0:
        return None
    if not isinstance(name, str) or not name.strip() or len(name) > 60:
        return None
    if isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0:
        return None
    try:
        finite_price = math.isfinite(price)
    except OverflowError:
        return None
    if not finite_price:
        return None
    if category not in ALLOWED_CATEGORIES:
        return None
    if not isinstance(description, str) or not description.strip() or len(description) > 120:
        return None
    if not isinstance(emoji, str) or not emoji or len(emoji) > 8:
        return None
    return {
        "id": product_id,
        "name": name.strip(),
        "price": price,
        "category": category,
        "description": description.strip(),
        "emoji": emoji,
    }


def make_handler(data_file=DATA_FILE, web_root=ROOT):
    data_file = Path(data_file)
    web_root = Path(web_root)

    class NovaStoreHandler(SimpleHTTPRequestHandler):
        storage_lock = threading.Lock()

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(web_root), **kwargs)

        def send_json(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def read_products(self):
            if not data_file.exists():
                return []
            with data_file.open(encoding="utf-8") as file:
                products = json.load(file)
            if not isinstance(products, list) or not all(validate_product(item) for item in products):
                raise ValueError("El archivo de productos del servidor tiene un formato no válido.")
            return products

        def do_GET(self):
            if self.path.split("?", 1)[0] != "/api/products":
                return super().do_GET()
            try:
                with self.storage_lock:
                    products = self.read_products()
                self.send_json(200, {"products": products})
            except (OSError, ValueError, json.JSONDecodeError) as error:
                self.send_json(500, {"error": str(error)})

        def do_POST(self):
            if self.path.split("?", 1)[0] != "/api/products":
                self.send_json(404, {"error": "Ruta API no encontrada."})
                return
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_json(400, {"error": "Longitud de solicitud no válida."})
                return
            if content_length <= 0 or content_length > 16384:
                self.send_json(413, {"error": "El tamaño de la solicitud no es válido."})
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self.send_json(400, {"error": "El cuerpo debe contener JSON válido."})
                return
            product = validate_product(payload)
            if product is None:
                self.send_json(400, {"error": "Los datos del producto no son válidos."})
                return
            try:
                with self.storage_lock:
                    products = self.read_products()
                    products = [item for item in products if item["id"] != product["id"]]
                    products.insert(0, product)
                    data_file.parent.mkdir(parents=True, exist_ok=True)
                    temporary_file = data_file.with_suffix(".tmp")
                    temporary_file.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
                    temporary_file.replace(data_file)
                self.send_json(200, {"product": product})
            except (OSError, ValueError, json.JSONDecodeError) as error:
                self.send_json(500, {"error": str(error)})

    return NovaStoreHandler


def main():
    address = ("127.0.0.1", 8000)
    server = ThreadingHTTPServer(address, make_handler())
    print(f"NovaStore disponible en http://{address[0]}:{address[1]} (Ctrl+C para detener)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
