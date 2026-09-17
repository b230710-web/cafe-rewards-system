"""
Automated Test Suite for Café Rewards Programme & Security Engine.
Tests points earning, tier multipliers (Regular -> Silver -> Gold),
redemptions, overdraft prevention, mathematical ledger audit, phone lookups,
Admin authentication, and catalog CRUD operations.
Pure Python unittest (zero external dependencies).
"""

import unittest
import os
import tempfile
import time
import database


class TestCafeRewardsProgramme(unittest.TestCase):

    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        database.init_database(self.temp_db_path)

    def tearDown(self):
        for _ in range(3):
            try:
                if os.path.exists(self.temp_db_path):
                    os.remove(self.temp_db_path)
                break
            except PermissionError:
                time.sleep(0.05)

    def test_admin_authentication_success_and_failure(self):
        """Verify default admin user can authenticate with password hashing."""
        # Default admin: admin / admin123
        user = database.verify_user_credentials("admin", "admin123", db_path=self.temp_db_path)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "admin")
        self.assertEqual(user["role"], "admin")

        # Wrong password must fail
        bad_user = database.verify_user_credentials("admin", "wrongpassword", db_path=self.temp_db_path)
        self.assertIsNone(bad_user)

        # Non-existent user must fail
        no_user = database.verify_user_credentials("nonexistent", "admin123", db_path=self.temp_db_path)
        self.assertIsNone(no_user)

    def test_member_registration_and_welcome_bonus(self):
        """Verify registration normalizes phone number and grants welcome bonus."""
        member = database.register_member(
            name="Alice Smith",
            phone="+91 98765-43210",
            email="alice@example.com",
            welcome_bonus=50,
            db_path=self.temp_db_path
        )
        self.assertEqual(member["name"], "Alice Smith")
        self.assertEqual(member["phone_normalized"], "919876543210")
        self.assertEqual(member["tier_name"], "Regular")
        self.assertEqual(member["current_balance"], 50)
        self.assertEqual(member["lifetime_points"], 50)
        self.assertTrue(member["audit_verified"])

    def test_customer_exact_phone_lookup(self):
        """Customer self-lookup widget should find member by phone accurately."""
        database.register_member("Hiya Tiwari", "+91 92575 38656", welcome_bonus=80, db_path=self.temp_db_path)
        found = database.get_member_by_phone_exact("9257538656", db_path=self.temp_db_path)
        self.assertIsNotNone(found)
        self.assertEqual(found["name"], "Hiya Tiwari")
        self.assertEqual(found["current_balance"], 80)

    def test_regular_tier_earning(self):
        """Regular tier should earn at 1.0x rate."""
        member = database.register_member("Bob Regular", "9123456780", welcome_bonus=0, db_path=self.temp_db_path)
        result = database.record_purchase(member["id"], order_amount=20.0, db_path=self.temp_db_path)
        self.assertEqual(result["points_earned"], 20)
        self.assertEqual(result["multiplier_applied"], 1.0)
        self.assertEqual(result["member"]["current_balance"], 20)

    def test_tier_promotion_to_silver(self):
        """Crossing 500 lifetime points should auto-promote to Silver (1.25x)."""
        member = database.register_member("Charlie Upgrader", "9123456781", welcome_bonus=0, db_path=self.temp_db_path)
        result = database.record_purchase(member["id"], order_amount=520.0, db_path=self.temp_db_path)
        self.assertTrue(result["tier_upgraded"])
        self.assertEqual(result["new_tier"], "Silver")
        self.assertEqual(result["member"]["points_multiplier"], 1.25)
        
        second_result = database.record_purchase(member["id"], order_amount=40.0, db_path=self.temp_db_path)
        self.assertEqual(second_result["points_earned"], 50)
        self.assertEqual(second_result["member"]["current_balance"], 520 + 50)

    def test_tier_promotion_to_gold(self):
        """Crossing 1500 lifetime points should auto-promote to Gold (1.50x)."""
        member = database.register_member("Diana VIP", "9123456782", welcome_bonus=0, db_path=self.temp_db_path)
        result = database.record_purchase(member["id"], order_amount=1600.0, db_path=self.temp_db_path)
        self.assertTrue(result["tier_upgraded"])
        self.assertEqual(result["new_tier"], "Gold")
        self.assertEqual(result["member"]["points_multiplier"], 1.50)

    def test_reward_redemption_and_overdraft_prevention(self):
        """Members cannot redeem items if balance is insufficient."""
        member = database.register_member("Evan Coffee", "9123456783", welcome_bonus=50, db_path=self.temp_db_path)
        catalog = database.get_rewards_catalog(db_path=self.temp_db_path)
        cappuccino = next(item for item in catalog if "Cappuccino" in item["item_name"])  # 150 pts
        
        # Insufficient points must fail
        with self.assertRaises(ValueError):
            database.redeem_reward(member["id"], cappuccino["id"], db_path=self.temp_db_path)

        # Give member points
        database.record_purchase(member["id"], order_amount=150.0, db_path=self.temp_db_path)  # +150 -> 200 pts
        redeem_res = database.redeem_reward(member["id"], cappuccino["id"], db_path=self.temp_db_path)
        self.assertTrue(redeem_res["success"])
        self.assertEqual(redeem_res["member"]["current_balance"], 50)

    def test_system_wide_audit_integrity(self):
        """System-wide audit should verify 0 discrepancies across all accounts."""
        m1 = database.register_member("User A", "9111111111", welcome_bonus=50, db_path=self.temp_db_path)
        m2 = database.register_member("User B", "9222222222", welcome_bonus=100, db_path=self.temp_db_path)

        database.record_purchase(m1["id"], 50.0, db_path=self.temp_db_path)
        database.record_purchase(m2["id"], 120.0, db_path=self.temp_db_path)

        audit = database.audit_entire_system(db_path=self.temp_db_path)
        self.assertTrue(audit["audit_passed"])
        self.assertEqual(audit["discrepancies_found"], 0)

    def test_admin_catalog_crud(self):
        """Admin can add new items to the rewards menu."""
        item = database.add_reward_item(
            item_name="Chocolate Glazed Eclair",
            category="Pastry",
            points_cost=180,
            retail_value=5.00,
            description="Crisp choux pastry filled with vanilla custard",
            icon="🥖",
            db_path=self.temp_db_path
        )
        self.assertIsNotNone(item["id"])
        self.assertEqual(item["item_name"], "Chocolate Glazed Eclair")

        # Verify appears in catalog
        catalog = database.get_rewards_catalog(db_path=self.temp_db_path)
        self.assertTrue(any(r["item_name"] == "Chocolate Glazed Eclair" for r in catalog))


if __name__ == "__main__":
    unittest.main(verbosity=2)
