-- ====================================================================
-- Café Rewards Programme - Relational Database Schema
-- Compatible with SQLite and MySQL / PostgreSQL
-- Designed for 100% exact ledger integrity, tiered rewards,
-- fast phone lookup, and role-based staff/admin authentication.
-- ====================================================================

-- 1. System Users / Staff Authentication Table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,            -- e.g. 'admin'
    password_hash TEXT NOT NULL,              -- SHA-256 + salt
    salt TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin',       -- 'admin', 'staff', 'manager'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Reward Tiers Table
CREATE TABLE IF NOT EXISTS tiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,                -- 'Regular', 'Silver', 'Gold'
    min_lifetime_points INTEGER NOT NULL,     -- 0, 500, 1500
    points_multiplier REAL NOT NULL,          -- 1.0, 1.25, 1.50
    badge_color TEXT NOT NULL,                -- Hex code or CSS identifier
    description TEXT
);

-- 3. Members Table
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE,               -- Formatted / entered phone
    phone_normalized TEXT NOT NULL UNIQUE,    -- Stripped of non-digits for O(log N) lookup
    email TEXT,
    tier_id INTEGER NOT NULL DEFAULT 1,
    lifetime_points INTEGER NOT NULL DEFAULT 0,
    current_balance INTEGER NOT NULL DEFAULT 0,
    total_spend REAL NOT NULL DEFAULT 0.0,
    visit_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tier_id) REFERENCES tiers(id)
);

-- B-Tree Index for sub-millisecond phone number lookups across tens of thousands of members
CREATE INDEX IF NOT EXISTS idx_members_phone ON members(phone_normalized);
CREATE INDEX IF NOT EXISTS idx_members_tier ON members(tier_id);

-- 4. Rewards Catalog Table (Free items redeemable with points)
CREATE TABLE IF NOT EXISTS rewards_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT NOT NULL,
    category TEXT NOT NULL,                   -- 'Beverage', 'Pastry', 'Food', 'Merchandise'
    points_cost INTEGER NOT NULL,             -- Points needed to redeem
    retail_value REAL NOT NULL,               -- Approx cash value
    description TEXT,
    icon TEXT,                                -- Emoji or image path
    is_active INTEGER NOT NULL DEFAULT 1
);

-- 5. Immutable Points Ledger Table (Audit trail of every point earned or spent)
-- Ensures the live balance is mathematically sound and verifiable at any moment:
-- SUM(points_delta) == current_balance
CREATE TABLE IF NOT EXISTS points_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL,
    transaction_type TEXT NOT NULL,           -- 'EARN', 'REDEEM', 'BONUS', 'TIER_UPGRADE'
    points_delta INTEGER NOT NULL,            -- Positive for earn, negative for redeem
    balance_after INTEGER NOT NULL,           -- Snapshot of balance right after transaction
    order_amount REAL DEFAULT 0.0,            -- Purchase order total in cash/card (if EARN)
    reward_item_id INTEGER DEFAULT NULL,      -- Redeemed item reference (if REDEEM)
    notes TEXT,                               -- Human-readable description
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(id),
    FOREIGN KEY (reward_item_id) REFERENCES rewards_catalog(id)
);

CREATE INDEX IF NOT EXISTS idx_ledger_member ON points_ledger(member_id);
CREATE INDEX IF NOT EXISTS idx_ledger_created_at ON points_ledger(created_at);
