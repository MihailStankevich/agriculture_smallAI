"""CropSignal MVP API. Standard library only; designed for a hackathon demo."""
from __future__ import annotations

import json
import math
import mimetypes
import threading
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
STORE = ROOT / "reports.json"
LOCK = threading.Lock()
RADIUS_KM = 12
WINDOW_DAYS = 7
MIN_REPORTS = 5


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_reports() -> list[dict]:
    if not STORE.exists():
        return []
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def write_reports(reports: list[dict]) -> None:
    STORE.write_text(json.dumps(reports, indent=2), encoding="utf-8")


def distance_km(a: dict, b: dict) -> float:
    """Haversine distance. Coordinates are already rounded by the client."""
    earth = 6371.0
    lat1, lon1 = math.radians(a["lat"]), math.radians(a["lon"])
    lat2, lon2 = math.radians(b["lat"]), math.radians(b["lon"])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * earth * math.asin(math.sqrt(h))


def valid_report(payload: dict) -> dict:
    label = str(payload.get("label", "")).strip()[:80]
    if not label:
        raise ValueError("A diagnosis label is required.")
    try:
        lat = round(float(payload["lat"]), 2)
        lon = round(float(payload["lon"]), 2)
        confidence = round(float(payload.get("confidence", 0)), 2)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid coordinates or confidence.") from exc
    if not (-90 <= lat <= 90 and -180 <= lon <= 180 and 0 <= confidence <= 1):
        raise ValueError("Report values are outside allowed limits.")
    allowed_observations = {"spreading", "wet", "many-plants", "underside"}
    observations = [str(item) for item in payload.get("observations", []) if str(item) in allowed_observations]
    language = str(payload.get("language", "en"))[:5]
    return {"id": payload.get("id") or f"r-{int(datetime.now().timestamp() * 1000)}", "label": label,
            "lat": lat, "lon": lon, "confidence": confidence, "observations": observations,
            "language": language, "createdAt": payload.get("createdAt") or now()}


def detect_outbreaks(reports: list[dict]) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    recent = []
    for report in reports:
        try:
            timestamp = datetime.fromisoformat(report["createdAt"].replace("Z", "+00:00"))
            if timestamp >= cutoff:
                recent.append(report)
        except (KeyError, ValueError):
            continue

    outbreaks = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for seed in recent:
        members = [r for r in recent if r["label"] == seed["label"] and distance_km(seed, r) <= RADIUS_KM]
        ids = tuple(sorted(r["id"] for r in members))
        key = (seed["label"], ids)
        if len(members) >= MIN_REPORTS and key not in seen:
            seen.add(key)
            outbreaks.append({
                "id": f"outbreak-{seed['label'].lower().replace(' ', '-')}",
                "label": seed["label"], "count": len(members),
                "lat": round(sum(r["lat"] for r in members) / len(members), 2),
                "lon": round(sum(r["lon"] for r in members) / len(members), 2),
                "radiusKm": RADIUS_KM, "windowDays": WINDOW_DAYS,
                "averageConfidence": round(sum(r["confidence"] for r in members) / len(members), 2),
                "observations": sorted({observation for report in members for observation in report.get("observations", [])}),
            })
    return outbreaks


def demo_reports() -> list[dict]:
    base_lat, base_lon = -1.2921, 36.8219  # Nairobi demo region, coordinates intentionally coarse
    cluster = [(0.01, 0.02), (-0.02, 0.03), (0.03, -0.02), (-0.03, -0.01), (0.01, -0.03), (0.04, 0.01)]
    isolated = [(0.46, 0.30, "Healthy"), (-0.38, -0.54, "Miner"), (0.66, -0.25, "Healthy")]
    reports = []
    for index, (lat, lon) in enumerate(cluster):
        reports.append({"id": f"demo-cluster-{index}", "label": "Leaf_rust", "lat": round(base_lat + lat, 2),
                        "lon": round(base_lon + lon, 2), "confidence": 0.84 + index * 0.01,
                        "observations": ["spreading", "underside"], "language": "sw", "createdAt": now()})
    for index, (lat, lon, label) in enumerate(isolated):
        reports.append({"id": f"demo-isolated-{index}", "label": label, "lat": round(base_lat + lat, 2),
                        "lon": round(base_lon + lon, 2), "confidence": 0.78,
                        "observations": [], "language": "en", "createdAt": now()})
    return reports


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store" if self.path.startswith("/api/") else "public, max-age=3600")
        super().end_headers()

    def send_json(self, data: object, status: int = HTTPStatus.OK) -> None:
        content = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/reports":
            with LOCK:
                self.send_json({"reports": read_reports()})
            return
        if path == "/api/outbreaks":
            with LOCK:
                reports = read_reports()
            self.send_json({"outbreaks": detect_outbreaks(reports), "rules": {"radiusKm": RADIUS_KM, "windowDays": WINDOW_DAYS, "minimumReports": MIN_REPORTS}})
            return
        return super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON."}, HTTPStatus.BAD_REQUEST)
            return
        with LOCK:
            if path == "/api/reports":
                try:
                    report = valid_report(payload)
                except ValueError as error:
                    self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
                    return
                reports = read_reports()
                if not any(item["id"] == report["id"] for item in reports):
                    reports.append(report)
                    write_reports(reports)
                self.send_json({"report": report, "outbreaks": detect_outbreaks(reports)}, HTTPStatus.CREATED)
                return
            if path == "/api/seed":
                # Replacing only prior generated demo rows keeps farmer-created
                # reports intact while ensuring the visible scenario is coffee.
                reports = [report for report in read_reports() if not str(report.get("id", "")).startswith("demo-")] + demo_reports()
                write_reports(reports)
                self.send_json({"reports": reports, "outbreaks": detect_outbreaks(reports)})
                return
            if path == "/api/reset":
                write_reports([])
                self.send_json({"reports": []})
                return
        self.send_json({"error": "Not found."}, HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    mimetypes.add_type("application/manifest+json", ".webmanifest")
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("CropSignal running at http://localhost:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
