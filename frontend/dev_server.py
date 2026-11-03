"""Local frontend preview with a same-origin proxy to FastAPI. No dependencies."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PUBLIC = Path(__file__).resolve().parent
ASSETS = {"/": "index.html", "/index.html": "index.html", "/styles.css": "styles.css", "/app.js": "app.js"}


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        name = ASSETS.get(self.path.split("?", 1)[0])
        if name is None:
            self.send_error(404)
            return
        self.path = "/" + name
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/analyze":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400)
            return
        if size <= 0 or size > 65536:
            self.send_error(413)
            return
        request = Request(
            "http://127.0.0.1:8000/api/analyze",
            data=self.rfile.read(size),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urlopen(request, timeout=95) as response:
                self.reply(response.status, response.read())
        except HTTPError as error:
            self.reply(error.code, error.read())
        except (URLError, TimeoutError):
            self.reply(502, b'{"detail":"Cannot reach the backend. Check that it is running on port 8000."}')

    def reply(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    def handler(*args, **kwargs):
        return Handler(*args, directory=str(PUBLIC), **kwargs)

    print("Sales Desk preview: http://127.0.0.1:8080", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8080), handler).serve_forever()
