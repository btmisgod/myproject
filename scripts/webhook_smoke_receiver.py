import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


HOST = "127.0.0.1"
PORT = 8799
LOG_PATH = Path("/tmp/agent-community-webhook-smoke.jsonl")


class WebhookSmokeHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            payload = {"raw_body": raw.decode("utf-8", errors="replace")}

        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

        envelope = payload.get("envelope", {}) if isinstance(payload, dict) else {}
        event_type = envelope.get("event_type")
        decision = ((envelope.get("metadata") or {}).get("protocol_validation") or {}).get("decision")
        print(f"received webhook event_type={event_type} decision={decision}")

        body = json.dumps({"ok": True}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return None


def main() -> None:
    server = HTTPServer((HOST, PORT), WebhookSmokeHandler)
    print(f"webhook smoke receiver listening on http://{HOST}:{PORT}/webhook")
    print(f"log file: {LOG_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
