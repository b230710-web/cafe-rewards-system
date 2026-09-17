"""
Database Setup & Migration Utility for Café Rewards Programme.
Initializes tables, seeds the default Administrator account, tiers, and rewards.
"""

import os
import sys
import database

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def setup():
    print("=" * 60)
    print("🚀 Initializing Café Rewards Database & Security Engine...")
    print("=" * 60)
    
    database.init_database()
    print("✅ Tables created from schema.sql:")
    print("   - users (Admin & Staff Authentication)")
    print("   - tiers (Regular 1.0x, Silver 1.25x, Gold 1.50x)")
    print("   - members (B-Tree indexed on phone_normalized)")
    print("   - rewards_catalog (Free items redeemable for points)")
    print("   - points_ledger (Immutable double-entry transaction trail)")

    print("\n🔐 Default Administrator Account Ready:")
    print("   👤 Admin ID / Username : admin")
    print("   🔑 Password           : admin123")
    print("   🛡️ Role               : System Administrator")
    print("=" * 60)


if __name__ == "__main__":
    setup()
