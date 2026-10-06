#!/usr/bin/env python3
import http.server
import json
from urllib.parse import urlparse, parse_qs

RATES = {
    "US": {"standard": 0.07, "name": "US State Sales Tax (Avg)", "is_eu": False},
    "GB": {"standard": 0.20, "name": "UK VAT", "is_eu": False},
    "DE": {"standard": 0.19, "name": "Germany MwSt", "is_eu": True},
    "FR": {"standard": 0.20, "name": "France TVA", "is_eu": True},
    "CA": {"standard": 0.13, "name": "Canada HST", "is_eu": False},
    "IN": {"standard": 0.18, "name": "India GST", "is_eu": False},
    "AU": {"standard": 0.10, "name": "Australia GST", "is_eu": False},
    "JP": {"standard": 0.10, "name": "Japan Consumption Tax", "is_eu": False}
}

class VATCalcHandler(http.server.BaseHTTPRequestHandler):
    def send_secure_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path == "/health":
            self.send_secure_json({"status": "healthy", "service": "VATCalc Global Tax API", "jurisdictions_supported": len(RATES)})
            return
        elif parsed.path == "/v1/rates":
            country = qs.get("country", ["US"])[0].upper()
            rate_info = RATES.get(country, {"standard": 0.0, "name": "Export Zero-Rate", "is_eu": False})
            self.send_secure_json({"country": country, **rate_info})
            return
        self.send_secure_json({"error": "Not Found"}, status=404)

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            self.send_secure_json({"error": "Malformed JSON"}, status=400)
            return

        amount = float(payload.get("amount", 100.0))
        country = str(payload.get("country", "US")).upper()
        is_b2b = bool(payload.get("is_b2b", False))

        rate_info = RATES.get(country, {"standard": 0.0, "name": "Zero-Rate", "is_eu": False})
        effective_rate = 0.0 if (is_b2b and rate_info["is_eu"]) else rate_info["standard"]
        tax_amount = round(amount * effective_rate, 2)
        gross_total = round(amount + tax_amount, 2)

        self.send_secure_json({
            "net_amount": amount,
            "tax_amount": tax_amount,
            "gross_amount": gross_total,
            "country": country,
            "tax_name": rate_info["name"],
            "rate_applied_pct": round(effective_rate * 100, 2),
            "reverse_charge_applied": is_b2b and rate_info["is_eu"]
        })

if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", 8080), VATCalcHandler)
    print("VATCalc API online on port 8080")
    server.serve_forever()
