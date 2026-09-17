# 🥐 Aurora Café Rewards & Multi-Slide Terminal

> **A high-reliability, multi-slide Point of Sale (POS) rewards terminal and double-entry points ledger built for café chains. Engineered with Python, Relational SQL (DBMS), and modern Vanilla HTML/CSS/JavaScript with ZERO Node.js or npm dependencies.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/Database-SQLite%20%2F%20MySQL%20Compatible-orange.svg)](schema.sql)
[![Dependencies](https://img.shields.io/badge/Dependencies-Zero%20External%20Packages-brightgreen.svg)](#quick-start)
[![Tests](https://img.shields.io/badge/Tests-100%25%20Passing-success.svg)](#running-tests)

---

## 🎨 Aesthetic Design & Theme
Styled directly after artisanal French bakery aesthetics:
- **Soft Pastel Sage / Pistachio Green** (`#E6ECE0`)
- **Warm Terracotta & Apricot Peach Cream** (`#F6D9C4`, `#DF8B57`)
- **Organic Scalloped Wavy Transitions**
- **High-contrast Typography**: Cormorant Garamond Serif & Plus Jakarta Sans

---

## 📑 3 Interactive Slides / Multi-View Navigation

### 1. Slide 1: Customer Rewards Experience & Bakery Landing
- Hero presentation with pastry tower composition and brand story.
- **"Check My Points" Live Customer Self-Lookup**: Members enter their phone number to see their live points balance, tier accelerator status, and points needed for their next free treat.
- **Organic Wavy Divider** flowing into the bakery showcase cards (Japanese Soufflé Berry Pancakes, Nitro Cold Brew Drizzle Cake, French Croissant).

### 2. Slide 2: Counter Staff Terminal (POS)
- Sub-millisecond phone number autocomplete with keyboard shortcut navigation (`/` to focus).
- Active Member Profile card with Tier badge (Regular, Silver, Gold), live points balance, and progress bar.
- **Record Purchase**: Enter bill total, calculates points earned with the active tier multiplier (1.0x, 1.25x, 1.50x), and auto-promotes member upon crossing milestones.
- **Redeem Free Rewards**: Visual menu shelf with overdraft protection preventing negative balances.
- **Live Transaction Ledger Table**: Real-time chronological audit stream.

### 3. Slide 3: Admin & Database Control Portal
- **Protected by Authentication**:
  - 👤 **Admin ID**: `admin`
  - 🔑 **Password**: `admin123`
  *(Salted SHA-256 password hashing and session tokens).*
- **Admin Management Capabilities**:
  - **Members Directory**: Filter by tier, search by name/phone, inspect balances, and open directly in POS.
  - **Rewards Catalog Management**: Add new menu items, update point prices, and toggle availability.
  - **1-Click System-Wide Audit**: Verifies that $\text{Live Balance} \equiv \sum \text{points\_delta}$ across all accounts in the database (0 discrepancies).
  - **Database Snapshot Export**: Download complete database JSON snapshot.

---

## 🚀 Quick Start (Zero Setup / No npm Required)

No Node.js, npm, or complex build tools needed. Runs directly using standard Python 3.

### 1. Run the Application
```bash
cd cafe_rewards
python app.py
```

Open your browser at:  
👉 **`http://localhost:5000`**

### 2. Administrator Login
- Navigate to the **Admin Portal** tab (Slide 3)
- Enter:
  - **Admin ID**: `admin`
  - **Password**: `admin123`

---

## 🧪 Running Automated Tests

Run the complete test suite verifying authentication, catalog CRUD, earning calculations, redemption overdraft prevention, and ledger audits:

```bash
python test_rewards.py
```

```text
test_admin_authentication_success_and_failure ... ok
test_admin_catalog_crud ... ok
test_customer_exact_phone_lookup ... ok
test_member_registration_and_welcome_bonus ... ok
test_regular_tier_earning ... ok
test_reward_redemption_and_overdraft_prevention ... ok
test_system_wide_audit_integrity ... ok
test_tier_promotion_to_gold ... ok
test_tier_promotion_to_silver ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.767s

OK (100% Passing)
```

---

## ⚡ Large-Scale Phone Lookup Benchmark

To test search speeds against **1,000+ realistic members**:

```bash
python seed_data.py
```
Average B-Tree indexed phone search speed: **$< 2.85\text{ ms}$**!

---

## 📁 Project Structure

```
cafe_rewards/
├── app.py                 # REST API & web server (authentication & routing)
├── database.py            # Relational database engine, auth, and ledger logic
├── schema.sql             # SQL DDL for users, tiers, members, catalog, and ledger
├── setup_db.py            # Database initialization and admin account creation
├── seed_data.py           # 1,000+ member generator & search benchmark
├── test_rewards.py        # Automated test suite (pure Python unittest)
├── requirements.txt       # Zero required pip packages
├── .gitignore             # Git ignore file for Python projects
├── static/
│   ├── css/
│   │   └── style.css      # Pastel sage & peach artisanal styling
│   └── js/
│       └── counter.js     # 3-slide controller, customer lookup, POS, & admin auth
└── templates/
    └── index.html         # 3-slide single page application template
```
