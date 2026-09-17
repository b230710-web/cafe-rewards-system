"""
Database, Ledger Engine & Security Module for Café Rewards Programme.
Designed for 100% exact live balance integrity, tiered earning multipliers,
immutable audit ledger, sub-millisecond phone lookups, and Admin authentication.
Zero external dependencies (pure Python standard library + relational SQL).
"""

import sqlite3
import re
import os
import hashlib
import secrets
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple, Any

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cafe_rewards.db")
SCHEMA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def normalize_phone(raw_phone: str) -> str:
    """Normalizes phone numbers by stripping all non-digit characters."""
    if not raw_phone:
        return ""
    return re.sub(r"\D", "", str(raw_phone))


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hashes password with SHA-256 and a cryptographic salt."""
    if not salt:
        salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((salt + password).encode("utf-8"))
    return hash_obj.hexdigest(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verifies a password attempt against stored hash and salt."""
    attempt_hash, _ = hash_password(password, salt)
    return attempt_hash == stored_hash


@contextmanager
def get_db(db_path: str = DB_FILE):
    """Context manager for SQLite connections ensuring clean closure."""
    conn = sqlite3.connect(db_path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()

# Convenient alias
get_connection = get_db


def init_database(db_path: str = DB_FILE) -> None:
    """Initializes schema, default admin user, tiers, and rewards."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        if os.path.exists(SCHEMA_FILE):
            with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
                cursor.executescript(f.read())

        # 1. Seed default Admin User (admin / admin123)
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            pw_hash, salt = hash_password("admin123")
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, salt, full_name, role)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("admin", pw_hash, salt, "Store Administrator", "admin")
            )
        
        # 2. Seed default tiers if empty
        cursor.execute("SELECT COUNT(*) FROM tiers")
        if cursor.fetchone()[0] == 0:
            tiers_data = [
                ("Regular", 0, 1.00, "#8D6E63", "Standard membership. Earn 1.0x base points per $1/₹10 spent."),
                ("Silver", 500, 1.25, "#64748B", "Silver Tier (500+ pts). Earn 1.25x points faster on every purchase!"),
                ("Gold", 1500, 1.50, "#D4AF37", "Gold Tier (1500+ pts). Earn 1.50x points faster + VIP rewards!")
            ]
            cursor.executemany(
                "INSERT INTO tiers (name, min_lifetime_points, points_multiplier, badge_color, description) VALUES (?, ?, ?, ?, ?)",
                tiers_data
            )

        # 3. Seed default rewards catalog if empty
        cursor.execute("SELECT COUNT(*) FROM rewards_catalog")
        if cursor.fetchone()[0] == 0:
            rewards_data = [
                ("Single Origin Espresso", "Beverage", 100, 3.50, "Rich, aromatic single-shot espresso", "☕"),
                ("Classic Cappuccino / Latte", "Beverage", 150, 4.75, "Steamed microfoam milk over double espresso", "🥛"),
                ("Artisanal Nitro Cold Brew", "Beverage", 200, 5.50, "Slow-steeped 18hr cold brew charged with nitrogen", "🧊"),
                ("Butter Flaky Croissant", "Pastry", 120, 3.75, "Warm, golden, flaky French butter croissant", "🥐"),
                ("Wild Blueberry Streusel Muffin", "Pastry", 140, 4.25, "Fresh baked muffin bursting with wild blueberries", "🧁"),
                ("Berry Chantilly Pancake Stack", "Pastry", 220, 6.50, "Fluffy Japanese style pancake with whipped cream and berries", "🥞"),
                ("Gourmet Avocado Sourdough Toast", "Food", 260, 7.50, "Artisan sourdough with seasoned avocado smash", "🥑"),
                ("Stainless Steel Café Tumbler", "Merchandise", 450, 18.00, "Insulated 16oz thermal travel tumbler", "🥤"),
                ("Single-Origin Beans Bag (250g)", "Merchandise", 650, 22.00, "Freshly roasted specialty coffee beans", "🫘")
            ]
            cursor.executemany(
                "INSERT INTO rewards_catalog (item_name, category, points_cost, retail_value, description, icon) VALUES (?, ?, ?, ?, ?, ?)",
                rewards_data
            )
        conn.commit()


# ====================================================================
# AUTHENTICATION & USER MANAGEMENT
# ====================================================================

def verify_user_credentials(username: str, password: str, db_path: str = DB_FILE) -> Optional[Dict[str, Any]]:
    """Validates user login against salted SHA-256 hash."""
    clean_user = username.strip().lower()
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = ?", (clean_user,))
        user = cursor.fetchone()
        if not user:
            return None

        if verify_password(password, user["password_hash"], user["salt"]):
            return {
                "id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user["role"]
            }
        return None


def create_user(username: str, password: str, full_name: str, role: str = "staff", db_path: str = DB_FILE) -> Dict[str, Any]:
    """Registers a new staff or admin user."""
    clean_user = username.strip().lower()
    pw_hash, salt = hash_password(password)
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, salt, full_name, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (clean_user, pw_hash, salt, full_name.strip(), role)
        )
        user_id = cursor.lastrowid
        conn.commit()
    return {"id": user_id, "username": clean_user, "full_name": full_name, "role": role}


# ====================================================================
# TIER MANAGEMENT & CALCULATIONS
# ====================================================================

def get_tier_for_points(lifetime_points: int, db_path: str = DB_FILE) -> Optional[Dict[str, Any]]:
    """Returns the highest tier matching the lifetime points threshold."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM tiers WHERE min_lifetime_points <= ? ORDER BY min_lifetime_points DESC LIMIT 1",
            (lifetime_points,)
        )
        tier = cursor.fetchone()
        if not tier:
            cursor.execute("SELECT * FROM tiers ORDER BY min_lifetime_points ASC LIMIT 1")
            tier = cursor.fetchone()
        return dict(tier) if tier else None


def get_all_tiers(db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """Returns all tiers ordered by progression threshold."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tiers ORDER BY min_lifetime_points ASC")
        return [dict(row) for row in cursor.fetchall()]


# ====================================================================
# MEMBER MANAGEMENT & HIGH-SPEED PHONE LOOKUP
# ====================================================================

def register_member(name: str, phone: str, email: Optional[str] = None, 
                    welcome_bonus: int = 50, db_path: str = DB_FILE) -> Dict[str, Any]:
    """Registers a new member with normalized phone indexing."""
    clean_name = name.strip()
    clean_phone = phone.strip()
    norm_phone = normalize_phone(clean_phone)

    if not clean_name:
        raise ValueError("Member name cannot be empty.")
    if len(norm_phone) < 6:
        raise ValueError("Valid phone number with at least 6 digits is required.")

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, phone FROM members WHERE phone_normalized = ?", (norm_phone,))
        existing = cursor.fetchone()
        if existing:
            raise ValueError(f"Member already registered with phone {clean_phone} (Member: {existing['name']})")

        cursor.execute("SELECT id FROM tiers ORDER BY min_lifetime_points ASC LIMIT 1")
        tier_row = cursor.fetchone()
        initial_tier_id = tier_row["id"] if tier_row else 1

        cursor.execute(
            """
            INSERT INTO members (name, phone, phone_normalized, email, tier_id, lifetime_points, current_balance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (clean_name, clean_phone, norm_phone, email.strip() if email else None, initial_tier_id, welcome_bonus, welcome_bonus)
        )
        member_id = cursor.lastrowid

        if welcome_bonus > 0:
            cursor.execute(
                """
                INSERT INTO points_ledger (member_id, transaction_type, points_delta, balance_after, notes)
                VALUES (?, 'BONUS', ?, ?, 'Welcome sign-up bonus points')
                """,
                (member_id, welcome_bonus, welcome_bonus)
            )

        conn.commit()

    return get_member_by_id(member_id, db_path)


def search_members_by_phone(query: str, limit: int = 15, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """High-speed member lookup by phone number or name."""
    query_str = query.strip()
    if not query_str:
        return []

    norm_query = normalize_phone(query_str)
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        if norm_query:
            cursor.execute(
                """
                SELECT m.*, t.name AS tier_name, t.points_multiplier, t.badge_color,
                       (SELECT COUNT(*) FROM points_ledger pl WHERE pl.member_id = m.id) AS transaction_count
                FROM members m
                JOIN tiers t ON m.tier_id = t.id
                WHERE m.phone_normalized LIKE ? OR m.name LIKE ?
                ORDER BY 
                    CASE 
                        WHEN m.phone_normalized = ? THEN 1
                        WHEN m.phone_normalized LIKE ? THEN 2
                        ELSE 3
                    END,
                    m.lifetime_points DESC
                LIMIT ?
                """,
                (f"%{norm_query}%", f"%{query_str}%", norm_query, f"{norm_query}%", limit)
            )
        else:
            cursor.execute(
                """
                SELECT m.*, t.name AS tier_name, t.points_multiplier, t.badge_color,
                       (SELECT COUNT(*) FROM points_ledger pl WHERE pl.member_id = m.id) AS transaction_count
                FROM members m
                JOIN tiers t ON m.tier_id = t.id
                WHERE m.name LIKE ?
                ORDER BY m.lifetime_points DESC
                LIMIT ?
                """,
                (f"%{query_str}%", limit)
            )

        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_member_by_phone_exact(phone_query: str, db_path: str = DB_FILE) -> Optional[Dict[str, Any]]:
    """Exact lookup by phone number for the Customer Portal self-service widget."""
    norm = normalize_phone(phone_query)
    if not norm:
        return None
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT m.id FROM members m
            WHERE m.phone_normalized = ? 
               OR m.phone_normalized LIKE ?
               OR ? LIKE '%' || m.phone_normalized
            ORDER BY LENGTH(m.phone_normalized) ASC
            LIMIT 1
            """,
            (norm, f"%{norm}", norm)
        )
        row = cursor.fetchone()
        if row:
            return get_member_by_id(row["id"], db_path)
        return None


def get_member_by_id(member_id: int, db_path: str = DB_FILE) -> Optional[Dict[str, Any]]:
    """Fetches full member details, tier progress metrics, and live audit confirmation."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT m.*, t.name AS tier_name, t.points_multiplier, t.badge_color, t.min_lifetime_points AS tier_min_points
            FROM members m
            JOIN tiers t ON m.tier_id = t.id
            WHERE m.id = ?
            """,
            (member_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        member = dict(row)

        cursor.execute(
            "SELECT * FROM tiers WHERE min_lifetime_points > ? ORDER BY min_lifetime_points ASC LIMIT 1",
            (member["lifetime_points"],)
        )
        next_tier = cursor.fetchone()
        if next_tier:
            points_needed = next_tier["min_lifetime_points"] - member["lifetime_points"]
            current_tier_base = member["tier_min_points"]
            tier_range = next_tier["min_lifetime_points"] - current_tier_base
            progress_in_tier = member["lifetime_points"] - current_tier_base
            progress_pct = min(100.0, max(0.0, (progress_in_tier / tier_range) * 100)) if tier_range > 0 else 100.0

            member["next_tier"] = {
                "name": next_tier["name"],
                "min_points": next_tier["min_lifetime_points"],
                "points_needed": points_needed,
                "progress_percentage": round(progress_pct, 1)
            }
        else:
            member["next_tier"] = None

        cursor.execute(
            "SELECT COALESCE(SUM(points_delta), 0) AS calculated_sum FROM points_ledger WHERE member_id = ?",
            (member_id,)
        )
        ledger_sum = cursor.fetchone()["calculated_sum"]
        stored_balance = member["current_balance"]

        member["audit_verified"] = (stored_balance == ledger_sum)
        member["ledger_sum"] = ledger_sum

        return member


def get_all_members_paginated(limit: int = 50, offset: int = 0, tier_id: Optional[int] = None,
                               query: Optional[str] = None, db_path: str = DB_FILE) -> Dict[str, Any]:
    """Admin endpoint for browsing and filtering all members."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        base_query = "FROM members m JOIN tiers t ON m.tier_id = t.id WHERE 1=1"
        params = []

        if tier_id:
            base_query += " AND m.tier_id = ?"
            params.append(tier_id)

        if query:
            clean_q = query.strip()
            norm_q = normalize_phone(clean_q)
            base_query += " AND (m.name LIKE ? OR m.phone_normalized LIKE ?)"
            params.extend([f"%{clean_q}%", f"%{norm_q}%"])

        cursor.execute(f"SELECT COUNT(*) {base_query}", params)
        total_count = cursor.fetchone()[0]

        cursor.execute(
            f"""
            SELECT m.*, t.name AS tier_name, t.badge_color,
                   (SELECT COUNT(*) FROM points_ledger pl WHERE pl.member_id = m.id) AS tx_count
            {base_query}
            ORDER BY m.id DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset]
        )
        rows = [dict(r) for r in cursor.fetchall()]

        return {
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "members": rows
        }


# ====================================================================
# TRANSACTIONAL REWARDS ENGINE (EARNING, TIERS, REDEMPTIONS)
# ====================================================================

def calculate_points_for_purchase(order_amount: float, multiplier: float) -> int:
    """Base Points = 1 point per $1 spent, multiplied by tier multiplier."""
    if order_amount <= 0:
        return 0
    calculated = int(round(order_amount * multiplier))
    return max(1, calculated)


def record_purchase(member_id: int, order_amount: float, notes: Optional[str] = None, 
                    db_path: str = DB_FILE) -> Dict[str, Any]:
    """Records a purchase at the counter with strict ACID guarantees."""
    if order_amount <= 0:
        raise ValueError("Order purchase amount must be greater than zero.")

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT m.*, t.name AS tier_name, t.points_multiplier
            FROM members m
            JOIN tiers t ON m.tier_id = t.id
            WHERE m.id = ?
            """,
            (member_id,)
        )
        member = cursor.fetchone()
        if not member:
            raise ValueError(f"Member with ID {member_id} not found.")

        current_balance = member["current_balance"]
        lifetime_points = member["lifetime_points"]
        old_tier_id = member["tier_id"]
        tier_multiplier = member["points_multiplier"]
        tier_name = member["tier_name"]

        points_earned = calculate_points_for_purchase(order_amount, tier_multiplier)
        new_balance = current_balance + points_earned
        new_lifetime_points = lifetime_points + points_earned
        new_total_spend = member["total_spend"] + order_amount
        new_visit_count = member["visit_count"] + 1

        cursor.execute(
            "SELECT * FROM tiers WHERE min_lifetime_points <= ? ORDER BY min_lifetime_points DESC LIMIT 1",
            (new_lifetime_points,)
        )
        highest_eligible_tier = cursor.fetchone()
        new_tier_id = highest_eligible_tier["id"] if highest_eligible_tier else old_tier_id
        tier_upgraded = (new_tier_id > old_tier_id)

        cursor.execute(
            """
            UPDATE members
            SET current_balance = ?,
                lifetime_points = ?,
                tier_id = ?,
                total_spend = ?,
                visit_count = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_balance, new_lifetime_points, new_tier_id, new_total_spend, new_visit_count, member_id)
        )

        purchase_note = notes or f"Purchase ${order_amount:.2f} (Earned at {tier_name} {tier_multiplier}x rate)"
        cursor.execute(
            """
            INSERT INTO points_ledger (member_id, transaction_type, points_delta, balance_after, order_amount, notes)
            VALUES (?, 'EARN', ?, ?, ?, ?)
            """,
            (member_id, points_earned, new_balance, order_amount, purchase_note)
        )
        ledger_id = cursor.lastrowid

        if tier_upgraded:
            upgrade_tier_name = highest_eligible_tier["name"]
            cursor.execute(
                """
                INSERT INTO points_ledger (member_id, transaction_type, points_delta, balance_after, notes)
                VALUES (?, 'TIER_UPGRADE', 0, ?, ?)
                """,
                (member_id, new_balance, f"🎉 Promoted to {upgrade_tier_name} Tier ({highest_eligible_tier['points_multiplier']}x multiplier)!")
            )

        conn.commit()

    updated_member = get_member_by_id(member_id, db_path)
    return {
        "success": True,
        "transaction_id": ledger_id,
        "points_earned": points_earned,
        "multiplier_applied": tier_multiplier,
        "tier_upgraded": tier_upgraded,
        "new_tier": highest_eligible_tier["name"] if tier_upgraded else tier_name,
        "member": updated_member
    }


def redeem_reward(member_id: int, reward_id: int, db_path: str = DB_FILE) -> Dict[str, Any]:
    """Redeems a reward item for points with strict validation."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rewards_catalog WHERE id = ? AND is_active = 1", (reward_id,))
        reward = cursor.fetchone()
        if not reward:
            raise ValueError(f"Reward item #{reward_id} does not exist or is inactive.")

        points_cost = reward["points_cost"]
        item_name = reward["item_name"]

        cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
        member = cursor.fetchone()
        if not member:
            raise ValueError(f"Member with ID {member_id} not found.")

        current_balance = member["current_balance"]
        if current_balance < points_cost:
            raise ValueError(
                f"Insufficient points! Member has {current_balance} pts, but '{item_name}' costs {points_cost} pts."
            )

        new_balance = current_balance - points_cost

        cursor.execute(
            """
            UPDATE members
            SET current_balance = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_balance, member_id)
        )

        cursor.execute(
            """
            INSERT INTO points_ledger (member_id, transaction_type, points_delta, balance_after, reward_item_id, notes)
            VALUES (?, 'REDEEM', ?, ?, ?, ?)
            """,
            (member_id, -points_cost, new_balance, reward_id, f"Redeemed: {item_name} ({reward['icon']})")
        )
        ledger_id = cursor.lastrowid
        conn.commit()

    updated_member = get_member_by_id(member_id, db_path)
    return {
        "success": True,
        "transaction_id": ledger_id,
        "redeemed_item": dict(reward),
        "points_spent": points_cost,
        "member": updated_member
    }


def get_member_ledger(member_id: int, limit: int = 50, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """Returns the chronological transaction ledger for a member."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT pl.*, rc.item_name, rc.icon AS reward_icon
            FROM points_ledger pl
            LEFT JOIN rewards_catalog rc ON pl.reward_item_id = rc.id
            WHERE pl.member_id = ?
            ORDER BY pl.id DESC
            LIMIT ?
            """,
            (member_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]


def audit_member_balance(member_id: int, db_path: str = DB_FILE) -> Dict[str, Any]:
    """Mathematical proof of balance integrity for a single member."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT current_balance FROM members WHERE id = ?", (member_id,))
        member_row = cursor.fetchone()
        if not member_row:
            return {"is_consistent": False, "error": "Member not found"}

        stored_balance = member_row["current_balance"]

        cursor.execute(
            "SELECT COALESCE(SUM(points_delta), 0) AS calculated_sum FROM points_ledger WHERE member_id = ?",
            (member_id,)
        )
        ledger_sum = cursor.fetchone()["calculated_sum"]

        return {
            "is_consistent": (stored_balance == ledger_sum),
            "stored_balance": stored_balance,
            "calculated_sum": ledger_sum,
            "difference": stored_balance - ledger_sum
        }


def audit_entire_system(db_path: str = DB_FILE) -> Dict[str, Any]:
    """
    Admin-level audit: Scans all member balances across the entire database
    to mathematically verify zero discrepancies between stored balances and ledger sums.
    """
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT m.id, m.name, m.phone, m.current_balance,
                   COALESCE(SUM(pl.points_delta), 0) AS ledger_sum,
                   (m.current_balance - COALESCE(SUM(pl.points_delta), 0)) AS discrepancy
            FROM members m
            LEFT JOIN points_ledger pl ON m.id = pl.member_id
            GROUP BY m.id
            HAVING discrepancy != 0
            """
        )
        discrepancies = [dict(r) for r in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) AS member_count FROM members")
        total_members = cursor.fetchone()["member_count"]

        return {
            "audit_passed": len(discrepancies) == 0,
            "total_accounts_audited": total_members,
            "discrepancies_found": len(discrepancies),
            "discrepant_accounts": discrepancies,
            "status": "100% Mathematical Integrity Confirmed" if len(discrepancies) == 0 else "Audit Alert: Discrepancies detected"
        }


# ====================================================================
# REWARDS CATALOG MANAGEMENT (ADMIN CRUD)
# ====================================================================

def get_rewards_catalog(include_inactive: bool = False, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """Returns catalog items."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM rewards_catalog"
        if not include_inactive:
            query += " WHERE is_active = 1"
        query += " ORDER BY points_cost ASC"
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]


def add_reward_item(item_name: str, category: str, points_cost: int, retail_value: float,
                    description: str = "", icon: str = "☕", db_path: str = DB_FILE) -> Dict[str, Any]:
    """Admin function to create a new reward item."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO rewards_catalog (item_name, category, points_cost, retail_value, description, icon)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (item_name.strip(), category.strip(), points_cost, retail_value, description.strip(), icon.strip())
        )
        new_id = cursor.lastrowid
        conn.commit()
        cursor.execute("SELECT * FROM rewards_catalog WHERE id = ?", (new_id,))
        return dict(cursor.fetchone())


def update_reward_item(item_id: int, item_name: str, category: str, points_cost: int,
                       retail_value: float, description: str, icon: str, is_active: int,
                       db_path: str = DB_FILE) -> Dict[str, Any]:
    """Admin function to update an existing reward item."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE rewards_catalog
            SET item_name = ?, category = ?, points_cost = ?, retail_value = ?,
                description = ?, icon = ?, is_active = ?
            WHERE id = ?
            """,
            (item_name.strip(), category.strip(), points_cost, retail_value, description.strip(), icon.strip(), is_active, item_id)
        )
        conn.commit()
        cursor.execute("SELECT * FROM rewards_catalog WHERE id = ?", (item_id,))
        return dict(cursor.fetchone())


def delete_reward_item(item_id: int, db_path: str = DB_FILE) -> bool:
    """Soft deletes or deactivates a reward item so past ledger records remain intact."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE rewards_catalog SET is_active = 0 WHERE id = ?", (item_id,))
        conn.commit()
        return cursor.rowcount > 0


# ====================================================================
# ANALYTICS & EXPORT ENGINE
# ====================================================================

def get_analytics_summary(db_path: str = DB_FILE) -> Dict[str, Any]:
    """Analytical aggregation for management / admin KPI view."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) AS total_members, COALESCE(SUM(current_balance), 0) AS total_points_liability, COALESCE(SUM(total_spend), 0) AS total_revenue FROM members")
        overview = dict(cursor.fetchone())

        cursor.execute(
            """
            SELECT 
                COALESCE(SUM(CASE WHEN points_delta > 0 THEN points_delta ELSE 0 END), 0) AS total_points_issued,
                COALESCE(SUM(CASE WHEN points_delta < 0 THEN ABS(points_delta) ELSE 0 END), 0) AS total_points_redeemed,
                COUNT(CASE WHEN transaction_type = 'EARN' THEN 1 END) AS total_purchase_events,
                COUNT(CASE WHEN transaction_type = 'REDEEM' THEN 1 END) AS total_redemption_events
            FROM points_ledger
            """
        )
        ledger_stats = dict(cursor.fetchone())

        cursor.execute(
            """
            SELECT t.name AS tier_name, t.badge_color, COUNT(m.id) AS member_count,
                   COALESCE(AVG(m.total_spend), 0.0) AS avg_spend
            FROM tiers t
            LEFT JOIN members m ON m.tier_id = t.id
            GROUP BY t.id, t.name, t.badge_color
            ORDER BY t.min_lifetime_points ASC
            """
        )
        tier_distribution = [dict(r) for r in cursor.fetchall()]

        return {
            "total_members": overview["total_members"],
            "total_revenue": round(overview["total_revenue"], 2),
            "total_points_in_circulation": overview["total_points_liability"],
            "total_points_issued": ledger_stats["total_points_issued"],
            "total_points_redeemed": ledger_stats["total_points_redeemed"],
            "redemption_rate_pct": round(
                (ledger_stats["total_points_redeemed"] / ledger_stats["total_points_issued"] * 100)
                if ledger_stats["total_points_issued"] > 0 else 0, 1
            ),
            "tier_distribution": tier_distribution
        }


def export_database_data(db_path: str = DB_FILE) -> Dict[str, Any]:
    """Exports full database snapshot for backup or data analytics exploration."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM members ORDER BY id ASC")
        members = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT * FROM tiers ORDER BY id ASC")
        tiers = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT * FROM rewards_catalog ORDER BY id ASC")
        rewards = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT * FROM points_ledger ORDER BY id DESC LIMIT 500")
        ledger = [dict(r) for r in cursor.fetchall()]

        return {
            "export_timestamp": str(os.path.getmtime(db_path) if os.path.exists(db_path) else ""),
            "members_count": len(members),
            "members": members,
            "tiers": tiers,
            "rewards_catalog": rewards,
            "recent_ledger": ledger
        }
