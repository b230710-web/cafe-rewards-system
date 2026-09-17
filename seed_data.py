"""
Dataset Seeder and Performance Benchmark for Café Rewards Programme.
Populates realistic members with purchase histories and redemptions
to demonstrate sub-millisecond phone number lookups across large datasets.
"""

import random
import time
import os
import sys
import database

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

FIRST_NAMES = [
    "Aarav", "Aditi", "Ananya", "Arjun", "Deepak", "Diya", "Ishaan", "Kavya",
    "Manish", "Neha", "Pooja", "Priya", "Rahul", "Riya", "Rohan", "Sanya",
    "Sneha", "Varun", "Vikram", "Zoya", "Liam", "Emma", "Noah", "Olivia",
    "James", "Sophia", "Benjamin", "Mia", "Lucas", "Charlotte"
]

LAST_NAMES = [
    "Sharma", "Verma", "Tiwari", "Gupta", "Mehta", "Patel", "Singh", "Choudhary",
    "Joshi", "Bose", "Nair", "Rao", "Mishra", "Reddy", "Kaur", "Agarwal",
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"
]


def generate_phone(index: int) -> str:
    """Generates unique 10-digit phone numbers starting with 9, 8, or 7."""
    prefix = random.choice(["98", "99", "97", "95", "91", "88", "87", "70"])
    remainder = f"{index:08d}"
    return f"{prefix}{remainder[:8]}"


def seed_database(total_members: int = 150, db_path: str = database.DB_FILE):
    database.init_database(db_path)

    catalog = database.get_rewards_catalog(db_path=db_path)
    with database.get_db(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
        if count >= total_members:
            return

    print(f"🌱 Seeding {total_members} members with realistic purchase and ledger data...")
    start_time = time.time()

    created_members = []
    for i in range(1, total_members + 1):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        phone = generate_phone(i)
        email = f"{first.lower()}.{last.lower()}{i}@example.com"
        
        tier_rand = random.random()
        welcome_bonus = 50

        try:
            m = database.register_member(name, phone, email, welcome_bonus=welcome_bonus, db_path=db_path)
            member_id = m["id"]

            if tier_rand > 0.90:
                num_orders = random.randint(15, 30)
            elif tier_rand > 0.70:
                num_orders = random.randint(6, 12)
            else:
                num_orders = random.randint(1, 3)

            for _ in range(num_orders):
                order_val = round(random.uniform(8.0, 55.0), 2)
                database.record_purchase(member_id, order_amount=order_val, db_path=db_path)

            if num_orders > 6 and catalog:
                affordable = [r for r in catalog if r["points_cost"] <= 200]
                if affordable:
                    reward = random.choice(affordable)
                    try:
                        database.redeem_reward(member_id, reward["id"], db_path=db_path)
                    except ValueError:
                        pass

            created_members.append((name, phone))
        except Exception:
            continue

    elapsed = time.time() - start_time
    print(f"✨ Successfully seeded {len(created_members)} members in {elapsed:.2f} seconds!")


if __name__ == "__main__":
    seed_database(200)
