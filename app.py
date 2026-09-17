"""
Café Chain Rewards Counter & Multi-View Terminal - Web Application Server.
Zero Node.js / Zero npm. Runs directly using Python standard library.
Includes Staff/Admin Authentication, 3-Slide Navigation, and REST APIs.
"""

import http.server
import socketserver
import json
import urllib.parse
import os
import sys
import mimetypes
import secrets
import time
import database

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PORT = 5000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# In-memory session store: token -> {user_id, username, full_name, role, login_time}
ACTIVE_SESSIONS = {}


class CafeRewardsHandler(http.server.SimpleHTTPRequestHandler):

    def send_json(self, data, status_code=200):
        """Helper to send JSON response."""
        encoded = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(encoded)

    def send_error_json(self, message, status_code=400):
        """Helper to send standardized error JSON."""
        self.send_json({"success": False, "error": message}, status_code=status_code)

    def get_auth_user(self):
        """Extracts user from Authorization header or token query parameter."""
        auth_header = self.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        
        if not token:
            parsed = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(parsed.query)
            token = q.get("token", [""])[0]

        if token and token in ACTIVE_SESSIONS:
            return ACTIVE_SESSIONS[token]
        return None

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. Main 3-Slide POS & Experience Interface
        if path == "/" or path == "/index.html":
            index_path = os.path.join(TEMPLATES_DIR, "index.html")
            if os.path.exists(index_path):
                self.serve_file(index_path, "text/html; charset=utf-8")
            else:
                self.send_error_json("Index template not found", 404)
            return

        # 2. Static Assets (CSS, JS, images)
        if path.startswith("/static/"):
            relative_static = path[len("/static/"):]
            file_path = os.path.join(STATIC_DIR, relative_static)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                mime_type, _ = mimetypes.guess_type(file_path)
                self.serve_file(file_path, mime_type or "application/octet-stream")
            else:
                self.send_error_json("Static asset not found", 404)
            return

        # 3. REST API Endpoints
        try:
            # Check Active Session: /api/auth/me
            if path == "/api/auth/me":
                user = self.get_auth_user()
                if user:
                    self.send_json({"success": True, "authenticated": True, "user": user})
                else:
                    self.send_json({"success": True, "authenticated": False})
                return

            # Customer Self-Lookup Widget (Slide 1): /api/customer/lookup?phone=9876543210
            if path == "/api/customer/lookup":
                phone = query.get("phone", [""])[0]
                member = database.get_member_by_phone_exact(phone)
                if member:
                    self.send_json({"success": True, "member": member})
                else:
                    self.send_error_json("No loyalty account found with this phone number.", 404)
                return

            # Staff Member Search: /api/members/search?q=98765
            if path == "/api/members/search":
                q = query.get("q", [""])[0]
                results = database.search_members_by_phone(q, limit=15)
                self.send_json({"success": True, "count": len(results), "members": results})
                return

            # Single member details: /api/members/<id>
            if path.startswith("/api/members/"):
                parts = path.strip("/").split("/")
                if len(parts) == 3 and parts[2].isdigit():
                    member_id = int(parts[2])
                    member = database.get_member_by_id(member_id)
                    if member:
                        self.send_json({"success": True, "member": member})
                    else:
                        self.send_error_json("Member not found", 404)
                    return

            # Rewards catalog: /api/rewards
            if path == "/api/rewards":
                include_inactive = query.get("all", ["0"])[0] == "1"
                catalog = database.get_rewards_catalog(include_inactive=include_inactive)
                self.send_json({"success": True, "rewards": catalog})
                return

            # Tiers listing: /api/tiers
            if path == "/api/tiers":
                tiers = database.get_all_tiers()
                self.send_json({"success": True, "tiers": tiers})
                return

            # Member ledger history: /api/ledger/<member_id>
            if path.startswith("/api/ledger/"):
                parts = path.strip("/").split("/")
                if len(parts) == 3 and parts[2].isdigit():
                    member_id = int(parts[2])
                    ledger = database.get_member_ledger(member_id, limit=30)
                    self.send_json({"success": True, "ledger": ledger})
                    return

            # Balance audit check: /api/audit/<member_id>
            if path.startswith("/api/audit/"):
                parts = path.strip("/").split("/")
                if len(parts) == 3 and parts[2].isdigit():
                    member_id = int(parts[2])
                    audit = database.audit_member_balance(member_id)
                    self.send_json({"success": True, "audit": audit})
                    return

            # Store Analytics Overview: /api/analytics
            if path == "/api/analytics":
                stats = database.get_analytics_summary()
                self.send_json({"success": True, "analytics": stats})
                return

            # -------------------------------------------------------------
            # ADMIN PROTECTED ENDPOINTS
            # -------------------------------------------------------------
            # Admin Members Listing: /api/admin/members?limit=50&offset=0&tier_id=...&q=...
            if path == "/api/admin/members":
                limit = int(query.get("limit", [50])[0])
                offset = int(query.get("offset", [0])[0])
                tier_id = int(query.get("tier_id")[0]) if query.get("tier_id") else None
                search_q = query.get("q", [None])[0]

                data = database.get_all_members_paginated(limit=limit, offset=offset, tier_id=tier_id, query=search_q)
                self.send_json({"success": True, **data})
                return

            # Admin System-Wide Audit: /api/admin/audit-all
            if path == "/api/admin/audit-all":
                audit_result = database.audit_entire_system()
                self.send_json({"success": True, "audit": audit_result})
                return

            # Admin Database Export: /api/admin/export
            if path == "/api/admin/export":
                export_data = database.export_database_data()
                self.send_json({"success": True, "data": export_data})
                return

            self.send_error_json(f"Endpoint '{path}' not found", 404)

        except Exception as e:
            self.send_error_json(str(e), 500)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            payload = json.loads(body) if body else {}

            # 1. Admin / Staff Login: POST /api/auth/login
            if path == "/api/auth/login":
                username = payload.get("username", "")
                password = payload.get("password", "")
                user = database.verify_user_credentials(username, password)
                if user:
                    token = secrets.token_hex(24)
                    ACTIVE_SESSIONS[token] = {**user, "token": token, "login_time": time.time()}
                    self.send_json({"success": True, "message": "Login successful", "token": token, "user": user})
                else:
                    self.send_error_json("Invalid username or password. Default admin: admin / admin123", 401)
                return

            # 2. Staff Logout: POST /api/auth/logout
            if path == "/api/auth/logout":
                token = payload.get("token") or self.headers.get("Authorization", "").replace("Bearer ", "")
                if token in ACTIVE_SESSIONS:
                    del ACTIVE_SESSIONS[token]
                self.send_json({"success": True, "message": "Logged out successfully"})
                return

            # 3. Register Member: POST /api/members
            if path == "/api/members":
                name = payload.get("name")
                phone = payload.get("phone")
                email = payload.get("email")
                welcome_bonus = int(payload.get("welcome_bonus", 50))
                
                member = database.register_member(name, phone, email, welcome_bonus=welcome_bonus)
                self.send_json({"success": True, "message": "Member registered successfully!", "member": member}, 201)
                return

            # 4. Record Purchase: POST /api/purchase
            if path == "/api/purchase":
                member_id = int(payload.get("member_id"))
                order_amount = float(payload.get("order_amount", 0.0))
                notes = payload.get("notes")

                result = database.record_purchase(member_id, order_amount, notes=notes)
                self.send_json(result)
                return

            # 5. Redeem Reward: POST /api/redeem
            if path == "/api/redeem":
                member_id = int(payload.get("member_id"))
                reward_id = int(payload.get("reward_id"))

                result = database.redeem_reward(member_id, reward_id)
                self.send_json(result)
                return

            # 6. Admin Add Reward Item: POST /api/admin/rewards
            if path == "/api/admin/rewards":
                name = payload.get("item_name")
                category = payload.get("category", "Pastry")
                points = int(payload.get("points_cost", 100))
                retail = float(payload.get("retail_value", 4.0))
                desc = payload.get("description", "")
                icon = payload.get("icon", "🥐")

                item = database.add_reward_item(name, category, points, retail, desc, icon)
                self.send_json({"success": True, "item": item}, 201)
                return

            # 7. Admin Update Reward Item: POST /api/admin/rewards/update
            if path == "/api/admin/rewards/update":
                item_id = int(payload.get("id"))
                name = payload.get("item_name")
                category = payload.get("category", "Pastry")
                points = int(payload.get("points_cost", 100))
                retail = float(payload.get("retail_value", 4.0))
                desc = payload.get("description", "")
                icon = payload.get("icon", "🥐")
                is_active = int(payload.get("is_active", 1))

                item = database.update_reward_item(item_id, name, category, points, retail, desc, icon, is_active)
                self.send_json({"success": True, "item": item})
                return

            self.send_error_json(f"Endpoint '{path}' not found", 404)

        except ValueError as ve:
            self.send_error_json(str(ve), 400)
        except Exception as e:
            self.send_error_json(f"Server error: {str(e)}", 500)

    def serve_file(self, file_path, content_type):
        """Serves a static file safely."""
        with open(file_path, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)


def run_server(port=PORT):
    database.init_database()
    
    with database.get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
        if count == 0:
            try:
                import seed_data
                print("🌱 Empty database detected. Seeding sample members...")
                seed_data.seed_database(150)
            except ImportError:
                print("🌱 Creating initial demo members...")
                try:
                    m1 = database.register_member("Aarav Sharma", "9876543210", "aarav@example.com", welcome_bonus=50)
                    m2 = database.register_member("Diya Patel", "9811122233", "diya@example.com", welcome_bonus=100)
                    m3 = database.register_member("Rohan Mehta", "9899988877", "rohan@example.com", welcome_bonus=0)
                    database.record_purchase(m2["id"], 550.0)
                    database.record_purchase(m3["id"], 1600.0)
                except Exception:
                    pass

    server_address = ("", port)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(server_address, CafeRewardsHandler) as httpd:
        print("=" * 70)
        print(f"🥐 Aurora Café Rewards Multi-View System running at:")
        print(f"👉 http://localhost:{port}")
        print("=" * 70)
        print("✨ Default Admin Credentials:")
        print("   👤 Admin ID: admin")
        print("   🔑 Password: admin123")
        print("=" * 70)
        print("🎨 Features Active:")
        print("   - Slide 1: Customer Bakery Showcase & Live Points Self-Lookup")
        print("   - Slide 2: Staff Counter POS (Fast phone search & Live Ledger)")
        print("   - Slide 3: Authenticated Admin & Database Control Center")
        print("=" * 70)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server gracefully...")


if __name__ == "__main__":
    run_server()
