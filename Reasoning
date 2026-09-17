# Reasoning — Café Rewards Programme

## 1. Problem Statement

The problem is to build a reliable rewards management system for a café chain.

The café has a rewards programme in which members earn points whenever they make a purchase. Members can move through different membership tiers such as Regular, Silver, and Gold. Higher tiers earn points at a faster rate.

The counter staff need to perform four important operations:

1. Look up a member using their phone number.
2. Record a purchase and calculate the correct reward points.
3. Allow members to redeem their available points for rewards.
4. Always display the correct live points balance.

The system must work reliably even when the café has a large number of members.

The main challenge is not only storing points, but ensuring that the balance is **always mathematically correct** after every purchase and redemption.

---

## 2. Understanding the Core Challenge

I broke the problem into two major areas:

### A. Reward Calculation

The system needs to determine how many points a member earns from a purchase.

The earning rate depends on the member's tier.

For example:

| Tier    | Points Multiplier |
| ------- | ----------------- |
| Regular | 1.0x              |
| Silver  | 1.5x              |
| Gold    | 2.0x              |

The calculation is based on the purchase amount:

```text
points earned = (purchase amount / 100) × tier multiplier
```

For example, if a Silver member spends ₹500:

```text
(500 / 100) × 1.5
= 7.5 points
```

Keeping this calculation in a separate service makes the reward logic easier to test and maintain.

---

### B. Maintaining the Correct Balance

The second and more important challenge is maintaining an accurate live balance.

For every purchase:

```text
new balance = old balance + earned points
```

For every redemption:

```text
new balance = old balance - redeemed points
```

The system must never allow:

```text
balance < 0
```

Therefore, redemption is allowed only when:

```text
available balance >= reward cost
```

This prevents invalid transactions and protects the integrity of the member's account.

---

# 3. Breaking the Problem into Components

Instead of putting all the logic into one large Python file, I divided the system into separate components.

```text
User Request
     |
     v
Application/API
     |
     +------------------+
     |                  |
     v                  v
Member Service      Reward Service
     |                  |
     |                  v
     |              Tier Logic
     |                  |
     +--------+---------+
              |
              v
           Database
              |
              v
        Transaction Ledger
```

The main components are:

### Member Management

Responsible for:

* Registering members
* Storing member information
* Finding members using phone numbers
* Maintaining their current tier
* Maintaining their points balance

### Reward Service

Responsible for:

* Calculating points earned from purchases
* Applying the correct tier multiplier

### Tier Service

Responsible for:

* Determining the member's tier
* Providing the earning multiplier for each tier

### Redemption Service

Responsible for:

* Checking the available balance
* Validating the redemption
* Deducting points
* Recording the transaction

### Database

Responsible for persistent storage of:

* Members
* Transactions
* Rewards
* Users/admin accounts

---

# 4. Choosing the Data Storage

I used a relational database because the application needs persistent and structured data.

The system contains different types of information:

```text
Members
Transactions
Rewards
Users
```

These are related to each other.

For example:

```text
Member
   |
   +---- Purchase Transaction
   |
   +---- Redemption Transaction
```

A relational database makes it possible to maintain these relationships and query the data efficiently.

SQLite is used for the current implementation because it is lightweight and easy to run locally without requiring a separate database server.

The design can later be migrated to PostgreSQL for a larger production deployment.

---

# 5. Designing the Member

Each member needs information such as:

```text
Member ID
Name
Phone Number
Email
Tier
Points Balance
Lifetime Points
```

The phone number is especially important because the counter staff use it to find a customer.

Therefore, the phone number should be treated as a unique identifier for customer lookup.

---

# 6. Designing the Transaction Ledger

I did not want the system to only store the final points balance.

Instead, every points-changing operation is recorded as a transaction.

For example:

```text
Purchase       +10 points
Redemption     -100 points
Purchase       +15 points
```

The transaction history provides an audit trail.

A simplified ledger can look like:

| Transaction | Points | Balance |
| ----------- | -----: | ------: |
| Purchase    |    +10 |     510 |
| Purchase    |    +15 |     525 |
| Redemption  |   -100 |     425 |

This makes it possible to understand how the current balance was generated.

---

# 7. Handling Tier Progression

The system determines the member's tier from their qualifying/lifetime points.

The current rules are:

```text
0+ points       → Regular
500+ points     → Silver
1000+ points    → Gold
```

The tier calculation is kept in one dedicated function.

Conceptually:

```python
if lifetime_points >= 1000:
    tier = "Gold"
elif lifetime_points >= 500:
    tier = "Silver"
else:
    tier = "Regular"
```

This prevents tier logic from being duplicated in multiple parts of the application.

If the café changes its tier thresholds later, the rules can be updated centrally.

---

# 8. Purchase Flow

When a customer makes a purchase, the system follows this sequence:

```text
1. Receive member phone number
             |
             v
2. Find member
             |
             v
3. Read current tier
             |
             v
4. Get tier multiplier
             |
             v
5. Calculate reward points
             |
             v
6. Update member points
             |
             v
7. Recalculate tier if required
             |
             v
8. Record purchase transaction
             |
             v
9. Return updated balance
```

For example:

```text
Member:
Silver

Purchase:
₹1000

Multiplier:
1.5x

Points:
(1000 / 100) × 1.5

= 15 points
```

The member's balance is then increased by 15 points.

---

# 9. Redemption Flow

Redemption follows a different validation process.

```text
Customer selects reward
          |
          v
Find member
          |
          v
Check current balance
          |
          v
Is balance >= reward cost?
       /             \
     YES              NO
      |                |
      v                v
Deduct points       Reject request
      |
      v
Record transaction
      |
      v
Return updated balance
```

For example:

```text
Current balance = 250
Reward cost = 200

250 >= 200
```

Therefore:

```text
New balance = 250 - 200
            = 50
```

But if:

```text
Current balance = 150
Reward cost = 200
```

the redemption is rejected.

The balance remains:

```text
150
```

This prevents negative balances.

---

# 10. Phone Number Lookup

The problem specifically mentions that the member list is long.

A simple implementation could scan every member:

```python
for member in members:
    if member.phone == phone:
        return member
```

However, this becomes inefficient as the number of members grows.

Therefore, the database uses indexed/efficient phone-number lookup.

Conceptually:

```text
Phone Number
     |
     v
Database Index
     |
     v
Member
```

This allows the counter to quickly find the required member without scanning the complete member list.

---

# 11. Authentication and Admin Portal

The application also contains an administrator area.

The admin portal provides functionality such as:

* Viewing members
* Managing rewards
* Viewing system information
* Running balance integrity checks
* Exporting system data

Authentication separates normal counter operations from administrative operations.

The default development administrator is:

```text
Admin ID: admin
Password: admin123
```

The application stores the password using a salted hash rather than storing the plain password directly.

For a production deployment, the default credentials should be changed and stored securely through environment configuration or a proper secrets manager.

---

# 12. Balance Integrity

One of the most important features is the balance integrity check.

The system can compare a member's stored balance against the transactions recorded in the ledger.

Conceptually:

```text
Expected Balance
=
Initial Points
+
Earned Points
-
Redeemed Points
```

For example:

```text
Initial = 50
Earned = 200
Redeemed = 75

Expected Balance
= 50 + 200 - 75
= 175
```

If the stored balance is also:

```text
175
```

the balance is consistent.

If it is different, the system can identify the account as requiring investigation.

This provides an additional layer of protection against data inconsistencies.

---

# 13. Handling Invalid Operations

A reliable system should not only handle valid input.

I considered invalid cases such as:

### Invalid purchase

```text
Purchase amount <= 0
```

The transaction is rejected.

### Unknown member

```text
Phone number does not exist
```

The system returns an appropriate error rather than creating an accidental account.

### Insufficient points

```text
Balance < reward cost
```

The redemption is rejected.

### Invalid tier

If an unsupported tier is supplied, the reward calculation should not silently continue.

Instead, the system raises an error.

### Duplicate phone number

Two members should not accidentally be created with the same phone number.

---

# 14. Testing Strategy

I used automated tests to verify the business rules independently from the user interface.

The tests cover areas such as:

```text
Reward calculation
Tier calculation
Member registration
Phone lookup
Purchase processing
Redemption
Insufficient balance
Authentication
Balance integrity
```

For example:

```python
assert calculate_points(500, "Regular") == 5
```

and:

```python
assert calculate_points(500, "Silver") == 7.5
```

Testing the core business rules separately makes it easier to identify problems before integrating the complete application.

---

# 15. Why I Chose This Approach

I followed a layered approach instead of putting everything into a single file.

The main reasons were:

### Separation of responsibilities

Each component has a specific purpose.

```text
Tier Service
     ↓
Tier rules

Reward Service
     ↓
Point calculation

Redemption Service
     ↓
Redemption validation

Database
     ↓
Persistent data
```

### Easier testing

Individual components can be tested independently.

### Easier maintenance

If the café changes its earning rules, the reward/tier logic can be changed without rewriting the entire application.

### Better scalability

The database and indexed lookup approach can handle a larger member list more efficiently than keeping all members in memory.

---

# 16. How the Solution Was Generated

I developed the solution incrementally rather than trying to build the complete application in one step.

The development process was:

```text
Problem Statement
       ↓
Identify Business Rules
       ↓
Define Members and Transactions
       ↓
Implement Tier Logic
       ↓
Implement Reward Calculation
       ↓
Implement Redemption Validation
       ↓
Design Database
       ↓
Connect Application to Database
       ↓
Add Member Lookup
       ↓
Add Authentication
       ↓
Build Counter Interface
       ↓
Build Admin Interface
       ↓
Add Automated Tests
       ↓
Run Integration Tests
       ↓
Package for Deployment
```

This approach helped isolate problems and verify each part before moving to the next stage.

---

# 17. Final Solution

The final system provides three main experiences:

### Customer View

Customers can:

* Look up their points
* See their tier
* View their rewards information

### Counter Staff View

Staff can:

* Search customers by phone number
* Record purchases
* Automatically calculate points
* Redeem rewards
* View the updated live balance
* View transaction history

### Admin View

Administrators can:

* Authenticate securely
* View the member database
* Manage the rewards catalogue
* Perform balance integrity checks
* Export system information

The overall system can therefore be represented as:

```text
                    CAFÉ REWARDS SYSTEM
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
         Customer       Counter        Admin
           View          Staff          Portal
             |             |             |
             +-------------+-------------+
                           |
                           v
                    Business Logic
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
          Rewards         Tier       Redemption
          Service        Service       Service
             |             |             |
             +-------------+-------------+
                           |
                           v
                       Database
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
          Members     Transactions     Rewards
```

The central design goal throughout the implementation is:

> **Every points-changing operation must follow the defined reward rules, be validated, update the member's balance correctly, and be recorded so that the balance can be audited later.**

This directly addresses the main requirement of the problem: **every member's points balance should always be exactly right.**
