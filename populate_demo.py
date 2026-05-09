"""Populate demo projects with realistic data for dashboard testing."""
import sqlite3

DB = "health_check.db"
conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = ON")
cur = conn.cursor()

# ============================================================
# Create additional roles needed for demo data
# ============================================================
print("=== Creating roles ===")
extra_roles = [
    (1, "Senior Developer", 1435.0),
    (1, "Backend Developer", 1200.0),
    (1, "Data Scientist", 1500.0),
    (1, "QA Engineer", 1100.0),
    (1, "Designer", 1250.0),
    (1, "DevOps Engineer", 1400.0),
    (1, "Product Manager", 1450.0),
]
for project_id, name, daily_rate in extra_roles:
    cur.execute(
        "INSERT INTO roles (project_id, name, daily_rate) VALUES (?, ?, ?)",
        (project_id, name, daily_rate)
    )
print(f"  Created {len(extra_roles)} additional roles")

# ============================================================
# PROJECT 1 — "AI-Powered Customer Support Platform"
# Agile feature dev, 120-day sprint, $150k budget
# ============================================================
print("\n=== Setting up Project 1 ===")
cur.execute("""
    UPDATE projects
    SET name = 'AI-Powered Customer Support Platform',
        description = 'Build an AI chatbot and support ticketing system to reduce response times by 60%. Includes NLP intent detection, auto-escalation, and live-agent handoff.',
        start_date = '2025-09-01',
        end_date = '2026-01-01',
        initial_budget = 150000.0,
        team_size = 5.0,
        health_on_track_pct = 65.0,
        health_at_risk_pct = 25.0
    WHERE id = 1
""")
print(f"  Updated project: {cur.rowcount} rows")

# Delete existing test data for project 1
cur.execute("DELETE FROM deliverables WHERE requirement_id IN (SELECT r.id FROM requirements r JOIN features f ON r.feature_id = f.id WHERE f.project_id = 1)")
cur.execute("DELETE FROM requirements WHERE feature_id IN (SELECT id FROM features WHERE project_id = 1)")
cur.execute("DELETE FROM features WHERE project_id = 1")
cur.execute("DELETE FROM capacity_periods WHERE project_id = 1")
cur.execute("DELETE FROM risks WHERE project_id = 1")

# Features for Project 1
features_p1 = [
    ("NLP Intent Detection Engine",     1, 1),
    ("Auto-Escalation Routing",         2, 1),
    ("Live-Agent Handoff Interface",    3, 1),
    ("Knowledge Base Search (RAG)",     4, 1),
    ("Multilingual Support (3 langs)",  5, 0),
    ("Analytics Dashboard",             6, 0),
    ("Mobile App Integration",          7, 0),
]

feature_ids_p1 = {}
for name, sort_order, started in features_p1:
    cur.execute(
        "INSERT INTO features (project_id, name, sort_order, started, expanded_scope) VALUES (1, ?, ?, ?, 0)",
        (name, sort_order, started)
    )
    fid = cur.lastrowid
    feature_ids_p1[name] = fid
    print(f"  Feature: \"{name}\" (id={fid})")

# Requirements for each feature
requirements_p1 = {
    "NLP Intent Detection Engine": [
        "Intent classification model (10 intent categories)",
        "Confidence scoring threshold configuration",
        "Model retraining pipeline",
        "Intent evaluation harness (precision/recall)",
    ],
    "Auto-Escalation Routing": [
        "Rule-based escalation engine",
        "SLA timer with reminders",
        "Escalation matrix for priority tiers",
        "Notification channel integration (Slack/email)",
    ],
    "Live-Agent Handoff Interface": [
        "Chat session transfer protocol",
        "Agent desktop with customer context",
        "Handoff notes template",
        "Post-handoff feedback collection",
    ],
    "Knowledge Base Search (RAG)": [
        "Document ingestion pipeline",
        "Vector embedding search",
        "Source citation display",
        "Answer confidence scoring",
        "Human review queue for low-confidence answers",
    ],
    "Multilingual Support (3 langs)": [
        "Translation model integration (ES/FR/DE)",
        "Locale-aware response formatting",
        "Cultural adaptation rules",
        "Translation quality assessment",
    ],
    "Analytics Dashboard": [
        "Conversation volume metrics",
        "Resolution rate tracking",
        "Customer satisfaction (CSAT) scores",
        "Agent performance metrics",
        "Export to CSV/PDF",
    ],
    "Mobile App Integration": [
        "Push notification service",
        "Mobile-optimized chat UI",
        "Offline message queue",
        "Biometric auth for agent app",
    ],
}

req_id_map = {}
for feat_name, req_names in requirements_p1.items():
    fid = feature_ids_p1[feat_name]
    for i, rname in enumerate(req_names):
        cur.execute(
            "INSERT INTO requirements (feature_id, name, sort_order, expanded_scope) VALUES (?, ?, ?, 0)",
            (fid, rname, i + 1)
        )
        req_id = cur.lastrowid
        req_id_map.setdefault(feat_name, []).append(req_id)

# Deliverables for each requirement
# Budget days per deliverable, and progress
deliverables_p1 = {
    "NLP Intent Detection Engine": [
        ("Intent classifier model training",  12,  85),
        ("Confidence scoring module",          6,   60),
        ("Retraining pipeline setup",          8,   40),
        ("Evaluation harness",                 6,   30),
    ],
    "Auto-Escalation Routing": [
        ("Rule engine core",                   8,  100),
        ("SLA timer implementation",           4,  100),
        ("Escalation matrix UI",               4,   75),
        ("Notification integration",           2,   50),
    ],
    "Live-Agent Handoff Interface": [
        ("Session transfer protocol",          6,   90),
        ("Agent desktop prototype",            8,   60),
        ("Handoff template system",            3,   80),
        ("Feedback collection flow",           3,   40),
    ],
    "Knowledge Base Search (RAG)": [
        ("Doc ingestion pipeline",             6,   50),
        ("Vector search integration",          8,   45),
        ("Citation display component",         4,   35),
        ("Confidence scoring",                 4,   30),
        ("Review queue UI",                    4,   20),
    ],
    "Multilingual Support (3 langs)": [
        ("Translation model setup",            6,   70),
        ("Locale formatting engine",           4,   40),
        ("Cultural adaptation rules",          4,   25),
        ("Quality assessment tool",            2,   10),
    ],
    "Analytics Dashboard": [
        ("Volume metrics widget",              3,   90),
        ("Resolution rate chart",              3,   80),
        ("CSAT scoring",                       4,   55),
        ("Agent perf tables",                  4,   50),
        ("Export functionality",               2,   30),
    ],
    "Mobile App Integration": [
        ("Push notification service",          4,   60),
        ("Mobile chat UI",                     6,   30),
        ("Offline queue",                      4,   20),
        ("Biometric auth",                     2,   10),
    ],
}

del_count = 0
for feat_name, dels in deliverables_p1.items():
    for fname, budget_days, progress in dels:
        fid = feature_ids_p1[feat_name]
        reqs = req_id_map.get(feat_name, [])
        rid = reqs[0] if reqs else None
        cur.execute(
            "INSERT INTO deliverables (requirement_id, name, budget_days, percent_complete, priority, sort_order, expanded_scope) VALUES (?, ?, ?, ?, 'high', ?, 0)",
            (rid, fname, budget_days, progress, del_count + 1)
        )
        del_count += 1
print(f"  Added {del_count} deliverables")

# Capacity entries for Project 1 — weekly capacity for 12 weeks
# Role IDs: 1=Senior Dev, 3=Data Scientist, 5=QA, 7=PM
capacity_data_p1 = [
    ("2025-09-01", 1, 2.0),  # 2 devs
    ("2025-09-01", 7, 0.5),  # 0.5 PM
    ("2025-09-01", 3, 1.0),  # 1 data scientist
    ("2025-09-08", 1, 2.0),
    ("2025-09-08", 7, 0.5),
    ("2025-09-08", 3, 1.0),
    ("2025-09-15", 1, 2.0),
    ("2025-09-15", 7, 0.5),
    ("2025-09-15", 3, 1.0),
    ("2025-09-22", 1, 2.0),
    ("2025-09-22", 7, 0.5),
    ("2025-09-22", 3, 1.0),
    ("2025-09-29", 1, 2.0),
    ("2025-09-29", 7, 0.5),
    ("2025-09-29", 3, 1.0),
    ("2025-10-06", 1, 2.0),
    ("2025-10-06", 7, 0.5),
    ("2025-10-06", 3, 0.5),
    ("2025-10-13", 1, 2.0),
    ("2025-10-13", 7, 0.5),
    ("2025-10-13", 5, 1.0),  # QA added
    ("2025-10-20", 1, 2.0),
    ("2025-10-20", 7, 0.5),
    ("2025-10-20", 5, 1.0),
    ("2025-10-27", 1, 2.0),
    ("2025-10-27", 7, 0.5),
    ("2025-10-27", 5, 1.0),
    ("2025-11-03", 1, 1.5),
    ("2025-11-03", 7, 0.5),
    ("2025-11-03", 5, 1.0),
    ("2025-11-10", 1, 1.5),
    ("2025-11-10", 7, 0.5),
    ("2025-11-10", 5, 1.0),
    ("2025-11-17", 1, 1.0),
    ("2025-11-17", 7, 0.5),
    ("2025-11-17", 5, 1.0),
    ("2025-11-24", 1, 1.0),
    ("2025-11-24", 7, 0.25),
    ("2025-11-24", 5, 1.0),
]

for week_start, role_id, team_size in capacity_data_p1:
    cur.execute(
        "INSERT INTO capacity_periods (project_id, week_start_date, role_id, team_size) VALUES (1, ?, ?, ?)",
        (week_start, role_id, team_size)
    )
print(f"  Added {len(capacity_data_p1)} capacity entries")

# Risks for Project 1
risks_p1 = [
    ("Model accuracy below target (90% precision)", 
     "NLP model may not reach 90% precision on intent detection with available training data. Would require more data collection or simplified intent categories.",
     "open", "2025-09-15", "2025-11-15", 15, 10),
    ("Third-party API rate limits", 
     "Translation API provider may impose unexpected rate limits, blocking multilingual rollout.",
     "open", "2025-10-01", "2025-12-01", 8, 5),
    ("Data privacy compliance review delay", 
     "Legal review of chat data retention policies may delay launch. GDPR and CCPA implications.",
     "open", "2025-09-20", "2025-11-30", 10, 14),
    ("Key developer availability", 
     "Lead data scientist has a 2-week leave in October for family reasons.",
     "realised", "2025-08-01", "2025-09-30", 6, 0),
]

for i, (rname, desc, status, date_id, due_date, impact, timeline) in enumerate(risks_p1):
    cur.execute(
        "INSERT INTO risks (project_id, name, description, status, date_identified, due_date, impact_days, timeline_impact_days, sort_order, realised_percentage) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (1, rname, desc, status, date_id, due_date, impact, timeline, i + 1, 0 if status == "open" else 100)
    )
print(f"  Added {len(risks_p1)} risks")

# Some actual spend
cur.execute("UPDATE projects SET actual_spend = 62500.0 WHERE id = 1")
print("  Actual spend set: $62,500")

# ============================================================
# PROJECT 2 — "E-commerce Platform Redesign"
# Agile feature dev, 90-day sprint, $200k budget
# ============================================================
print("\n=== Setting up Project 2 ===")
cur.execute("""
    UPDATE projects
    SET description = 'Complete redesign of checkout flow, product pages, search, and admin dashboard. Migrate from legacy monolith to microservices architecture for the backend.',
        start_date = '2025-10-15',
        end_date = '2026-01-15',
        initial_budget = 200000.0,
        team_size = 8.0,
        health_on_track_pct = 50.0,
        health_at_risk_pct = 35.0,
        accent = 'emerald',
        icon = 'cart'
    WHERE id = 2
""")
print(f"  Updated project: {cur.rowcount} rows")

# Delete existing test data for project 2
cur.execute("DELETE FROM deliverables WHERE requirement_id IN (SELECT r.id FROM requirements r JOIN features f ON r.feature_id = f.id WHERE f.project_id = 2)")
cur.execute("DELETE FROM requirements WHERE feature_id IN (SELECT id FROM features WHERE project_id = 2)")
cur.execute("DELETE FROM features WHERE project_id = 2")
cur.execute("DELETE FROM capacity_periods WHERE project_id = 2")
cur.execute("DELETE FROM risks WHERE project_id = 2")

# Features for Project 2
features_p2 = [
    ("New Checkout Flow",             1, 1),
    ("Product Page Redesign",         2, 1),
    ("Search & Discovery Engine",     3, 1),
    ("Admin Dashboard v2",            4, 0),
    ("Microservices Migration (auth)",5, 0),
    ("Microservices Migration (orders)", 6, 0),
    ("Payment Gateway Integration",   7, 0),
    ("Mobile Responsive Overhaul",    8, 0),
]

feature_ids_p2 = {}
for name, sort_order, started in features_p2:
    cur.execute(
        "INSERT INTO features (project_id, name, sort_order, started, expanded_scope) VALUES (2, ?, ?, ?, 0)",
        (name, sort_order, started)
    )
    fid = cur.lastrowid
    feature_ids_p2[name] = fid
    print(f"  Feature: \"{name}\" (id={fid})")

# Requirements for Project 2
requirements_p2 = {
    "New Checkout Flow": [
        "One-page checkout redesign",
        "Guest checkout option",
        "Address auto-completion",
        "Order summary & review step",
        "Abandoned cart recovery email",
    ],
    "Product Page Redesign": [
        "New product image gallery (360°)",
        "Variant selector (size/color)",
        "Related products carousel",
        "Customer review section",
        "Stock availability indicator",
    ],
    "Search & Discovery Engine": [
        "Autocomplete search suggestions",
        "Faceted filtering (price, brand, rating)",
        "Product ranking algorithm",
        "Search analytics dashboard",
        "Synonym dictionary management",
    ],
    "Admin Dashboard v2": [
        "Order management interface",
        "Inventory tracking",
        "Customer analytics",
        "Revenue reports with filters",
        "User role management",
    ],
    "Microservices Migration (auth)": [
        "OAuth2 token service",
        "User profile service",
        "Session management",
        "SSO integration",
    ],
    "Microservices Migration (orders)": [
        "Order placement service",
        "Order state machine",
        "Fulfillment tracking",
        "Return/refund handler",
    ],
    "Payment Gateway Integration": [
        "Stripe API integration",
        "PayPal integration",
        "Payment webhook handling",
        "Fraud detection hooks",
    ],
    "Mobile Responsive Overhaul": [
        "Responsive layout system",
        "Touch-optimized navigation",
        "Mobile checkout flow",
        "Performance optimization (Lighthouse > 90)",
    ],
}

req_id_map_p2 = {}
for feat_name, req_names in requirements_p2.items():
    fid = feature_ids_p2[feat_name]
    for i, rname in enumerate(req_names):
        cur.execute(
            "INSERT INTO requirements (feature_id, name, sort_order, expanded_scope) VALUES (?, ?, ?, 0)",
            (fid, rname, i + 1)
        )
        req_id = cur.lastrowid
        req_id_map_p2.setdefault(feat_name, []).append(req_id)

# Deliverables for Project 2
deliverables_p2 = {
    "New Checkout Flow": [
        ("Checkout wireframes",            4,   90),
        ("Guest checkout implementation",   6,   60),
        ("Address auto-complete (Google)",  4,   75),
        ("Review step component",           3,   50),
        ("Cart recovery email template",    3,   20),
    ],
    "Product Page Redesign": [
        ("Image gallery component",         6,   70),
        ("Variant selector",                4,   60),
        ("Related products API + UI",       5,   40),
        ("Reviews section",                 4,   35),
        ("Stock indicator",                 2,   25),
    ],
    "Search & Discovery Engine": [
        ("Autocomplete service",            6,   55),
        ("Faceted search UI",               6,   40),
        ("Ranking algorithm v1",            8,   25),
        ("Search analytics",                4,   15),
        ("Synonym manager",                 2,    5),
    ],
    "Admin Dashboard v2": [
        ("Order management UI",             6,   45),
        ("Inventory tracking",              5,   30),
        ("Customer analytics views",        5,   20),
        ("Revenue reports",                 4,   15),
        ("Role management",                 3,    5),
    ],
    "Microservices Migration (auth)": [
        ("OAuth2 token service",            8,   20),
        ("User profile service",            6,   15),
        ("Session management",              4,   10),
        ("SSO integration",                 6,    5),
    ],
    "Microservices Migration (orders)": [
        ("Order placement service",         8,   12),
        ("State machine",                   6,    8),
        ("Fulfillment tracking",            6,    5),
        ("Return/refund handler",           4,    3),
    ],
    "Payment Gateway Integration": [
        ("Stripe SDK setup & tests",        4,   40),
        ("PayPal SDK setup & tests",        4,   30),
        ("Webhook processing",              4,   15),
        ("Fraud detection hooks",           3,    5),
    ],
    "Mobile Responsive Overhaul": [
        ("Responsive CSS framework",        6,   50),
        ("Touch navigation",                4,   35),
        ("Mobile checkout",                 5,   25),
        ("Performance audit + fixes",       6,   20),
    ],
}

del_count_p2 = 0
for feat_name, dels in deliverables_p2.items():
    for fname, budget_days, progress in dels:
        fid = feature_ids_p2[feat_name]
        reqs = req_id_map_p2.get(feat_name, [])
        rid = reqs[0] if reqs else None
        cur.execute(
            "INSERT INTO deliverables (requirement_id, name, budget_days, percent_complete, priority, sort_order, expanded_scope) VALUES (?, ?, ?, ?, 'high', ?, 0)",
            (rid, fname, budget_days, progress, del_count_p2 + 1)
        )
        del_count_p2 += 1
print(f"  Added {del_count_p2} deliverables")

# Capacity entries for Project 2
# Role IDs: 2=Backend Dev, 4=Designer, 5=QA, 7=PM
capacity_data_p2 = [
    ("2025-10-15", 2, 3.0),  # 3 backend devs
    ("2025-10-15", 4, 1.0),  # 1 designer
    ("2025-10-15", 7, 0.5),  # 0.5 PM
    ("2025-10-22", 2, 3.0),
    ("2025-10-22", 4, 1.0),
    ("2025-10-22", 7, 0.5),
    ("2025-10-29", 2, 3.0),
    ("2025-10-29", 4, 1.0),
    ("2025-10-29", 5, 1.0),  # QA added
    ("2025-11-05", 2, 3.0),
    ("2025-11-05", 4, 1.0),
    ("2025-11-05", 5, 1.0),
    ("2025-11-12", 2, 3.0),
    ("2025-11-12", 4, 1.0),
    ("2025-11-12", 5, 1.0),
    ("2025-11-19", 2, 3.0),
    ("2025-11-19", 4, 0.5),
    ("2025-11-19", 7, 0.5),
    ("2025-11-19", 5, 1.0),
    ("2025-11-26", 2, 2.5),
    ("2025-11-26", 4, 0.5),
    ("2025-11-26", 7, 0.5),
    ("2025-11-26", 5, 1.0),
    ("2025-12-03", 2, 2.0),
    ("2025-12-03", 7, 0.5),
    ("2025-12-03", 5, 1.0),
    ("2025-12-10", 2, 2.0),
    ("2025-12-10", 7, 0.5),
    ("2025-12-10", 5, 1.0),
    ("2025-12-17", 2, 1.5),
    ("2025-12-17", 7, 0.25),
    ("2025-12-17", 5, 1.0),
]

for week_start, role_id, team_size in capacity_data_p2:
    cur.execute(
        "INSERT INTO capacity_periods (project_id, week_start_date, role_id, team_size) VALUES (2, ?, ?, ?)",
        (week_start, role_id, team_size)
    )
print(f"  Added {len(capacity_data_p2)} capacity entries")

# Risks for Project 2
risks_p2 = [
    ("Legacy data migration complexity",
     "Customer order history from legacy system has inconsistent data formats. Migration scripts may need extensive rework.",
     "open", "2025-10-20", "2025-12-31", 12, 14),
    ("Payment processor downtime risk",
     "Stripe/PayPal outage during launch week would block all transactions. Need fallback processor.",
     "open", "2025-11-01", "2026-01-15", 5, 7),
    ("Scope creep from marketing team",
     "Marketing has requested additional feature: loyalty program, which is not in scope but under pressure to include.",
     "open", "2025-11-10", "2026-01-15", 20, 21),
    ("Third-party analytics API changes",
     "Google Analytics 4 API made breaking changes mid-sprint, requiring rework of search analytics dashboard.",
     "realised", "2025-10-01", "2025-11-15", 4, 3),
]

for i, (rname, desc, status, date_id, due_date, impact, timeline) in enumerate(risks_p2):
    cur.execute(
        "INSERT INTO risks (project_id, name, description, status, date_identified, due_date, impact_days, timeline_impact_days, sort_order, realised_percentage) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (2, rname, desc, status, date_id, due_date, impact, timeline, i + 1, 0 if status == "open" else 100)
    )
print(f"  Added {len(risks_p2)} risks")

# Some actual spend for project 2
cur.execute("UPDATE projects SET actual_spend = 55000.0 WHERE id = 2")
print("  Actual spend set: $55,000")

# Add decisions
decisions = [
    (1, "Choose Stripe over PayPal as primary processor", "Stripe has better API docs and lower fees for our volume", "2025-09-10", "technology", 1, "Lower transaction costs, better developer experience"),
    (2, "Adopt microservices for checkout first", "Checkout is the highest revenue impact area", "2025-10-20", "architecture", 1, "Faster time to revenue impact from new checkout"),
    (2, "Use React for admin dashboard", "Team has React expertise, faster delivery", "2025-10-25", "technology", 1, "Reduced learning curve, quicker MVP"),
]

for proj_id, name, desc, date, dtype, sort_order, outcome in decisions:
    cur.execute(
        "INSERT INTO decisions (project_id, name, description, decision_date, decision_type, sort_order, expected_outcome) VALUES (?,?,?,?,?,?,?)",
        (proj_id, name, desc, date, dtype, sort_order, outcome)
    )
print(f"  Added {len(decisions)} decisions")

# Add milestones
milestones = [
    (1, "NLP Model Beta Ready", "Intent detection model reaches 85% precision", 25000, 1),
    (1, "First 100 Live Users", "Chatbot handles 100 real customer conversations", 0, 2),
    (1, "Full Launch", "All features released to production", 0, 3),
    (2, "New Checkout Beta", "New checkout live for 10% of users", 15000, 1),
    (2, "Microservices Phase 1", "Auth + Orders services deployed", 20000, 2),
    (2, "Platform Launch", "Full redesign live, legacy shutdown", 0, 3),
]

for pid, name, desc, value, sort_order in milestones:
    cur.execute(
        "INSERT INTO milestones (project_id, name, description, value, sort_order) VALUES (?, ?, ?, ?, ?)",
        (pid, name, desc, value, sort_order)
    )
print(f"  Added {len(milestones)} milestones")

# Add overhead entries
overheads = [
    ("Project Manager Retainer", 3000.0, "2025-09-01", "2026-01-01", "monthly"),
    ("NLP API License", 1500.0, "2025-09-01", "2026-01-01", "monthly"),
    ("Project Manager Retainer", 4000.0, "2025-10-15", "2026-01-15", "monthly"),
    ("Analytics Tool License", 800.0, "2025-10-15", "2026-01-15", "monthly"),
    ("CDN Service", 500.0, "2025-10-15", "2026-01-15", "monthly"),
]

for name, amount, start, end, freq in overheads:
    cur.execute(
        "INSERT INTO overheads (name, amount, start_date, end_date, frequency) VALUES (?, ?, ?, ?, ?)",
        (name, amount, start, end, freq)
    )
print(f"  Added {len(overheads)} overheads")

# Add budget adjustments
cur.execute(
    "INSERT INTO budget_adjustments (project_id, name, amount, date, description) VALUES (?, ?, ?, ?, ?)",
    (2, "Additional QA headcount", -5000.0, "2025-11-01", "Added 1 QA engineer for 2 months")
)
cur.execute(
    "INSERT INTO budget_adjustments (project_id, name, amount, date, description) VALUES (?, ?, ?, ?, ?)",
    (1, "NLP API license increase", -2000.0, "2025-10-15", "Additional API tier for production")
)
print("  Added 2 budget adjustments")

conn.commit()
conn.close()

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 50)
print("=== SUMMARY ===")
print("=" * 50)
conn = sqlite3.connect(DB)
cur = conn.cursor()

for pid in [1, 2]:
    cur.execute("SELECT name, initial_budget, actual_spend, start_date, end_date FROM projects WHERE id = ?", (pid,))
    row = cur.fetchone()
    print(f"\nProject {pid}: {row[0]}")
    print(f"  Budget: ${row[1]:,.0f}  |  Spend: ${row[2]:,.0f}")
    print(f"  Period: {row[3]} to {row[4]}")
    
    cur.execute("SELECT COUNT(*) FROM features WHERE project_id = ?", (pid,))
    print(f"  Features: {cur.fetchone()[0]}")
    
    cur.execute("""SELECT COUNT(*) FROM deliverables d 
        JOIN requirements r ON d.requirement_id = r.id 
        JOIN features f ON r.feature_id = f.id 
        WHERE f.project_id = ?""", (pid,))
    print(f"  Deliverables: {cur.fetchone()[0]}")
    
    cur.execute("""SELECT COUNT(*) FROM requirements r 
        JOIN features f ON r.feature_id = f.id 
        WHERE f.project_id = ?""", (pid,))
    print(f"  Requirements: {cur.fetchone()[0]}")
    
    cur.execute("SELECT COUNT(*) FROM capacity_periods WHERE project_id = ?", (pid,))
    print(f"  Capacity entries: {cur.fetchone()[0]}")
    
    cur.execute("SELECT COUNT(*) FROM risks WHERE project_id = ?", (pid,))
    print(f"  Risks: {cur.fetchone()[0]}")
    
    cur.execute("SELECT COUNT(*) FROM decisions WHERE project_id = ?", (pid,))
    print(f"  Decisions: {cur.fetchone()[0]}")
    
    cur.execute("SELECT COUNT(*) FROM milestones WHERE project_id = ?", (pid,))
    print(f"  Milestones: {cur.fetchone()[0]}")
    
    cur.execute("SELECT COUNT(*) FROM budget_adjustments WHERE project_id = ?", (pid,))
    print(f"  Budget adjustments: {cur.fetchone()[0]}")

# Overall totals
cur.execute("SELECT COUNT(*) FROM features")
print(f"\nTotal Features (all projects): {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM deliverables")
print(f"Total Deliverables (all projects): {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM risks")
print(f"Total Risks (all projects): {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM capacity_periods")
print(f"Total Capacity entries (all projects): {cur.fetchone()[0]}")

conn.close()
print("\n✅ Demo data population complete!")
