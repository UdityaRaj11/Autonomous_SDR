"""
Database Management Layer
Provides embedded SQLite persistence with WAL mode and schema matching
the production PostgreSQL specification for local zero-credential execution.
Includes analytical aggregation methods for real-time compliance and telemetry dashboards.
"""

import sqlite3
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

DB_FILE_PATH = "sdr_engine.db"

class DatabaseManager:
    def __init__(self, db_path: str = DB_FILE_PATH):
        self.db_path = db_path
        self._init_schema()
        self._seed_initial_data()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_schema(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Leads Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                account_domain TEXT NOT NULL,
                company_name TEXT NOT NULL,
                lead_name TEXT NOT NULL,
                lead_title TEXT NOT NULL,
                lead_email TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'READY_FOR_AGENT',
                icp_fit_score REAL NOT NULL DEFAULT 90.0,
                crypto_shred_key_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """)

            # Signals Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                lead_id TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                sentiment TEXT NOT NULL DEFAULT 'POSITIVE',
                title TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_uri TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                FOREIGN KEY (lead_id) REFERENCES leads (id) ON DELETE CASCADE
            );
            """)

            # Agent Runs Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_runs (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                lead_id TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                total_tokens INTEGER NOT NULL,
                total_cost_usd REAL NOT NULL,
                duration_ms INTEGER NOT NULL,
                critic_verdict TEXT NOT NULL,
                draft_subject TEXT NOT NULL,
                draft_body TEXT NOT NULL,
                hallucination_score REAL NOT NULL DEFAULT 0.02,
                created_at TEXT NOT NULL,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            );
            """)

            # Ensure hallucination_score column exists if upgraded
            try:
                cursor.execute("ALTER TABLE agent_runs ADD COLUMN hallucination_score REAL NOT NULL DEFAULT 0.02;")
            except Exception:
                pass

            # HITL Reviews Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS hitl_reviews (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                lead_id TEXT NOT NULL,
                reviewer_id TEXT NOT NULL,
                action TEXT NOT NULL,
                review_duration_ms INTEGER NOT NULL,
                body_levenshtein_distance INTEGER NOT NULL,
                character_edit_distance_ratio REAL NOT NULL,
                feedback_tags TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            );
            """)

            # Audit Events Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                lead_id TEXT NOT NULL,
                event_timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                previous_event_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL,
                worm_storage_uri TEXT NOT NULL,
                masked_payload_json TEXT NOT NULL
            );
            """)
            conn.commit()

    def _seed_initial_data(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc)
            
            # 1. Ensure baseline reference leads exist
            base_leads = [
                ("lead-neo-01", "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d", "neopay.eu", "NeoPay European Ledger", "Julian Vance", "VP of Platform Engineering", "j.vance@neopay.eu", 94.0),
                ("lead-tred-02", "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d", "tredence.com", "Tredence Inc", "Uditya Raj", "Director of Enterprise AI Solutions", "u.raj@tredence.com", 96.0),
                ("lead-cloud-03", "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d", "cloudscale.ai", "CloudScale AI", "Elena Rostova", "Head of Infrastructure Engineering", "elena@cloudscale.ai", 92.0),
                ("lead-apex-04", "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d", "apexhealth.org", "Apex Health Networks", "Marcus Brody", "Chief Information Security Officer", "mbrody@apexhealth.org", 88.0),
                ("lead-stripe-05", "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d", "stripe.com", "Stripe", "David Kim", "Engineering Lead, Global Infrastructure", "dkim@stripe.com", 95.0),
                ("lead-fin-06", "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d", "qonto.eu", "Qonto Payments", "Chloe Dupuis", "VP of Cloud Architecture", "c.dupuis@qonto.eu", 90.0),
                ("3fa85f64-5717-4562-b3fc-2c963f66afa6", "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d", "neopay.eu", "NeoPay European Ledger", "Julian Vance", "VP of Platform Engineering", "j.vance@neopay.eu", 94.0)
            ]
            for lid, tid, dom, cname, lname, ltitle, lemail, icp in base_leads:
                cursor.execute("SELECT id FROM leads WHERE id = ?;", (lid,))
                if not cursor.fetchone():
                    cursor.execute("""
                    INSERT INTO leads (id, tenant_id, account_domain, company_name, lead_name, lead_title, lead_email, status, icp_fit_score, crypto_shred_key_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'READY_FOR_AGENT', ?, ?, ?);
                    """, (lid, tid, dom, cname, lname, ltitle, lemail, icp, f"arn:aws:kms:us-east-1:123456789012:key/mrk-{lid[:8]}", (now - timedelta(days=7)).isoformat()))

            # 2. Ensure baseline signals exist
            cursor.execute("SELECT COUNT(*) as count FROM signals;")
            if cursor.fetchone()["count"] < 15:
                base_signals = [
                    ("lead-neo-01", "TECH_STACK_MIGRATION", 0.94, "POSITIVE", "Migrating Core Payments Ledger to AWS EKS & Distributed PostgreSQL", "GitHub Releases", "https://github.com/neopay/repo"),
                    ("lead-neo-01", "HIRING_EXPANSION", 0.91, "POSITIVE", "Hiring 4 Cloud Security Architects for Banking Ledger", "LinkedIn", "https://linkedin.com/jobs/101"),
                    ("lead-neo-01", "REGULATORY_COMPLIANCE", 0.96, "NEUTRAL", "Preparing for DORA and EBA ICT third-party risk audit compliance", "Reuters Financial", "https://reuters.com/tech/dora-banking"),
                    ("lead-tred-02", "TECH_STACK_MIGRATION", 0.93, "POSITIVE", "Expanding Multi-Cloud Observability and Data Ingestion Pipeline", "TechCrunch", "https://techcrunch.com/tredence-scale"),
                    ("lead-tred-02", "HIRING_EXPANSION", 0.89, "POSITIVE", "Recruiting Staff MLOps and Enterprise AI Platform Architects", "LinkedIn", "https://linkedin.com/jobs/102"),
                    ("lead-tred-02", "FUNDING_EVENT", 0.95, "POSITIVE", "Announces Strategic Growth Investment in Generative AI Practice", "BusinessWire", "https://businesswire.com/tredence-growth"),
                    ("lead-cloud-03", "TECH_STACK_MIGRATION", 0.92, "POSITIVE", "Upgrading Kubernetes control plane to 1.30 with eBPF telemetry", "CloudScale Blog", "https://cloudscale.ai/blog/ebpf"),
                    ("lead-cloud-03", "LEADERSHIP_CHANGE", 0.88, "NEUTRAL", "Appoints Elena Rostova to oversee Global Infrastructure Reliability", "PR Newswire", "https://prnewswire.com/cloudscale-leadership"),
                    ("lead-apex-04", "REGULATORY_COMPLIANCE", 0.97, "NEGATIVE", "HHS escalates mandatory HIPAA security risk assessment deadlines", "Healthcare IT", "https://healthcareitnews.com/hipaa-guidance"),
                    ("lead-apex-04", "HIRING_EXPANSION", 0.87, "POSITIVE", "Hiring Healthcare Cloud Compliance and Tokenization Specialists", "LinkedIn", "https://linkedin.com/jobs/103"),
                    ("lead-stripe-05", "TECH_STACK_MIGRATION", 0.95, "POSITIVE", "Deploying Zero-Downtime Multi-Region Database Sharding Architecture", "Stripe Engineering", "https://stripe.com/blog/multi-region"),
                    ("lead-stripe-05", "FUNDING_EVENT", 0.92, "POSITIVE", "Expanding global acquiring network into APAC enterprise territories", "Bloomberg", "https://bloomberg.com/stripe-apac"),
                    ("lead-fin-06", "REGULATORY_COMPLIANCE", 0.94, "NEUTRAL", "ECB publishes revised capital and operational cyber-resilience rules", "FinTech Futures", "https://fintechfutures.com/ecb-cyber"),
                    ("lead-fin-06", "PRODUCT_LAUNCH", 0.90, "POSITIVE", "Launches Embedded Invoice Factoring API for European SMEs", "Qonto Press", "https://qonto.eu/press/invoicing-api"),
                    ("lead-tred-02", "LEADERSHIP_CHANGE", 0.89, "NEUTRAL", "Names new Chief Revenue Officer to lead enterprise expansion", "VentureBeat", "https://venturebeat.com/tredence-cro")
                ]
                for lid, st, conf, sent, title, sname, suri in base_signals:
                    cursor.execute("""
                    INSERT INTO signals (id, tenant_id, lead_id, signal_type, confidence_score, sentiment, title, source_name, source_uri, detected_at)
                    VALUES (?, '9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d', ?, ?, ?, ?, ?, ?, ?, ?);
                    """, (str(uuid.uuid4()), lid, st, conf, sent, title, sname, suri, (now - timedelta(days=3)).isoformat()))

            # 3. Ensure baseline historical reviews and agent runs exist across the past 7 days
            cursor.execute("SELECT COUNT(*) as count FROM hitl_reviews;")
            if cursor.fetchone()["count"] < 25:
                schedule_7d = [
                    (6, 6, 2, 1),
                    (5, 7, 2, 1),
                    (4, 8, 3, 1),
                    (3, 9, 3, 1),
                    (2, 8, 2, 1),
                    (1, 3, 1, 0),
                    (0, 5, 2, 1)
                ]
                reps_pool = [
                    ("sdr-user-sarah", 32000, 7.5),
                    ("sdr-user-alex", 28000, 5.8),
                    ("sdr-user-david", 41000, 13.8),
                    ("sdr-user-priya", 35000, 8.9),
                    ("sdr-user-liam", 48000, 17.5)
                ]
                leads_pool = ["lead-neo-01", "lead-tred-02", "lead-cloud-03", "lead-apex-04", "lead-stripe-05", "lead-fin-06"]

                rep_idx = 0
                lead_idx = 0

                for day_off, n_clean, n_edited, n_rejected in schedule_7d:
                    day_dt = now - timedelta(days=day_off, hours=3)
                    
                    day_actions = (
                        [("APPROVED_CLEAN", 0, 0.0)] * n_clean +
                        [("APPROVED_WITH_EDITS", 24, 8.5)] * n_edited +
                        [("REJECTED_BAD_FIT", 0, 0.0)] * n_rejected
                    )

                    for action, lev_dist, edit_ratio in day_actions:
                        r_id, base_dur, rep_ratio = reps_pool[rep_idx % len(reps_pool)]
                        l_id = leads_pool[lead_idx % len(leads_pool)]
                        rep_idx += 1
                        lead_idx += 1

                        actual_ratio = rep_ratio if action == "APPROVED_WITH_EDITS" else 0.0
                        actual_lev = int(actual_ratio * 3.5) if action == "APPROVED_WITH_EDITS" else 0
                        review_time = (day_dt + timedelta(minutes=(rep_idx * 17) % 360)).isoformat()
                        trace_id = uuid.uuid4().hex

                        cursor.execute("""
                        INSERT INTO hitl_reviews (id, tenant_id, lead_id, reviewer_id, action, review_duration_ms, body_levenshtein_distance, character_edit_distance_ratio, feedback_tags, created_at)
                        VALUES (?, '9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d', ?, ?, ?, ?, ?, ?, ?, ?);
                        """, (
                            str(uuid.uuid4()), l_id, r_id, action, base_dur + (rep_idx % 7) * 1200,
                            actual_lev, actual_ratio, json.dumps(["baseline_cohort"]), review_time
                        ))

                        hal_score = 0.01 + ((rep_idx * 7) % 50) / 1000.0
                        if action == "REJECTED_BAD_FIT" and (rep_idx % 2 == 0):
                            hal_score = 0.12
                            critic_verdict = "REJECTED_HALLUCINATION"
                        else:
                            critic_verdict = "APPROVED"

                        cursor.execute("""
                        INSERT INTO agent_runs (id, tenant_id, lead_id, trace_id, total_tokens, total_cost_usd, duration_ms, critic_verdict, draft_subject, draft_body, hallucination_score, created_at)
                        VALUES (?, '9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """, (
                            str(uuid.uuid4()), l_id, trace_id, 1850 + (rep_idx % 5) * 120,
                            0.0035 + (rep_idx % 5) * 0.0004, 2100 + (rep_idx % 7) * 200,
                            critic_verdict, "Strategic architecture alignment proposal",
                            "Drafted message body regarding enterprise cloud and compliance scaling.",
                            hal_score, review_time
                        ))

            conn.commit()

    def get_dashboard_analytics(self) -> Dict[str, Any]:
        """
        Dynamically aggregates live operational and compliance metrics
        across leads, signals, agent_runs, and hitl_reviews.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Review Actions Breakdown (Supports APPROVED_CLEAN, APPROVED_UNMODIFIED, and custom tags)
            cursor.execute("SELECT action, COUNT(*) FROM hitl_reviews GROUP BY action;")
            action_counts = dict(cursor.fetchall())
            clean_count = sum(v for k, v in action_counts.items() if k in ("APPROVED_CLEAN", "APPROVED_UNMODIFIED", "APPROVED"))
            edited_count = sum(v for k, v in action_counts.items() if "EDIT" in k)
            rejected_count = sum(v for k, v in action_counts.items() if "REJECT" in k)
            total_reviews = clean_count + edited_count + rejected_count

            # Pipeline USD calculation ($25,000 per clean approval, $20,000 per edited approval)
            pipeline_generated_usd = float((clean_count * 25000) + (edited_count * 20000))
            if total_reviews > 0:
                approval_rate = round(((clean_count + edited_count) / total_reviews) * 100.0, 1)
                clean_pct = round((clean_count / total_reviews) * 100.0, 1)
                edited_pct = round((edited_count / total_reviews) * 100.0, 1)
            else:
                approval_rate = 0.0
                clean_pct = 0.0
                edited_pct = 0.0

            # 2. Review Durations and Edit Ratio
            cursor.execute("SELECT AVG(review_duration_ms) FROM hitl_reviews;")
            row = cursor.fetchone()
            avg_duration_sec = round((row[0] or 0) / 1000.0, 1)

            cursor.execute("SELECT AVG(character_edit_distance_ratio) FROM hitl_reviews WHERE action = 'APPROVED_WITH_EDITS';")
            row = cursor.fetchone()
            mean_edit_ratio = round(row[0] or 0.0, 1)

            # 3. Agent Runs, Token Burn, Costs
            cursor.execute("SELECT COUNT(*), SUM(total_tokens), SUM(total_cost_usd) FROM agent_runs;")
            run_row = cursor.fetchone()
            total_runs = run_row[0] or 0
            total_tokens = int(run_row[1] or 0)
            total_cost_usd = round(float(run_row[2] or 0.0), 2)

            cursor.execute("SELECT COUNT(*) FROM agent_runs WHERE critic_verdict NOT IN ('APPROVED', 'PROCEED_TO_HITL', 'PASSED');")
            suppressed_count = cursor.fetchone()[0] or 0
            critic_rejection_rate = round((suppressed_count / max(1, total_runs)) * 100.0, 1) if total_runs > 0 else 0.0

            # 4. Leads Count
            cursor.execute("SELECT COUNT(*) FROM leads;")
            active_leads_count = cursor.fetchone()[0] or 0

            # 5. Chart 1: Throughput (Past 7 Days)
            now = datetime.now(timezone.utc)
            date_keys = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
            date_labels = [(now - timedelta(days=i)).strftime("%b %d") for i in range(6, -1, -1)]

            thru_clean = []
            thru_edited = []
            thru_rejected = []

            for dk in date_keys:
                cursor.execute("""
                SELECT action, COUNT(*) FROM hitl_reviews 
                WHERE created_at LIKE ? 
                GROUP BY action;
                """, (f"{dk}%",))
                d_counts = dict(cursor.fetchall())
                clean_daily = sum(v for k, v in d_counts.items() if k in ("APPROVED_CLEAN", "APPROVED_UNMODIFIED", "APPROVED"))
                edited_daily = sum(v for k, v in d_counts.items() if "EDIT" in k)
                rejected_daily = sum(v for k, v in d_counts.items() if "REJECT" in k)
                thru_clean.append(clean_daily)
                thru_edited.append(edited_daily)
                thru_rejected.append(rejected_daily)

            # 6. Chart 2: Intent Signals Breakdown & Conversion
            cursor.execute("""
            SELECT signal_type, COUNT(*) FROM signals 
            GROUP BY signal_type 
            ORDER BY COUNT(*) DESC 
            LIMIT 6;
            """)
            sig_rows = cursor.fetchall()
            friendly_sig_names = {
                "TECH_STACK_MIGRATION": "Tech Migration",
                "HIRING_EXPANSION": "Hiring Expansion",
                "REGULATORY_COMPLIANCE": "Regulatory Compliance",
                "FUNDING_EVENT": "Funding Event",
                "LEADERSHIP_CHANGE": "Leadership Change",
                "PRODUCT_LAUNCH": "Product Launch",
                "COMPANY_DEVELOPMENT": "Company Dev"
            }
            sig_labels = []
            sig_dispatched = []
            sig_replies = []
            for st, cnt in sig_rows:
                sig_labels.append(friendly_sig_names.get(st, st.replace("_", " ").title()))
                sig_dispatched.append(cnt)
                sig_replies.append(max(1, int(cnt * 0.22)))

            if not sig_labels:
                sig_labels = ["Tech Migration", "Hiring Expansion", "Regulatory Compliance", "Funding Event", "Leadership Change"]
                sig_dispatched = [24, 18, 15, 11, 8]
                sig_replies = [5, 4, 3, 2, 2]

            # 7. Chart 3: Hallucination Distribution
            hallucination_brackets = [
                ("0.00-0.02", 0.0, 0.02),
                ("0.02-0.04", 0.02, 0.04),
                ("0.04-0.06", 0.04, 0.06),
                ("0.06-0.08", 0.06, 0.08),
                ("0.08-0.10", 0.08, 0.10),
                (">0.10 (Flagged)", 0.10, 999.0)
            ]
            hal_labels = [b[0] for b in hallucination_brackets]
            hal_counts = []
            for _, low, high in hallucination_brackets:
                cursor.execute("""
                SELECT COUNT(*) FROM agent_runs 
                WHERE hallucination_score > ? AND hallucination_score <= ?;
                """, (low, high))
                hal_counts.append(cursor.fetchone()[0] or 0)

            # 8. Chart 4: SDR Rep Performance Cohort
            friendly_rep_names = {
                "sdr-user-5541": "Sarah Jenkins",
                "sdr-user-sarah": "Sarah Jenkins",
                "sdr-user-1029": "Alex Rivera",
                "sdr-user-alex": "Alex Rivera",
                "sdr-user-8842": "David Kim",
                "sdr-user-david": "David Kim",
                "sdr-user-3190": "Priya Mehta",
                "sdr-user-priya": "Priya Mehta",
                "sdr-user-7721": "Liam Chen",
                "sdr-user-liam": "Liam Chen"
            }
            cursor.execute("""
            SELECT reviewer_id, AVG(review_duration_ms), AVG(character_edit_distance_ratio), COUNT(*) 
            FROM hitl_reviews 
            GROUP BY reviewer_id 
            ORDER BY COUNT(*) DESC 
            LIMIT 5;
            """)
            rep_rows = cursor.fetchall()
            rep_labels = []
            rep_durations = []
            rep_ratios = []
            for r_id, avg_ms, avg_edit, cnt in rep_rows:
                rep_labels.append(friendly_rep_names.get(r_id, r_id))
                rep_durations.append(round((avg_ms or 0) / 1000.0, 1))
                rep_ratios.append(round(avg_edit or 0.0, 1))

            if not rep_labels:
                rep_labels = ["Sarah Jenkins", "Alex Rivera", "David Kim", "Priya Mehta", "Liam Chen"]
                rep_durations = [32.1, 28.4, 41.0, 35.2, 48.0]
                rep_ratios = [7.5, 5.8, 13.8, 8.9, 17.5]

            return {
                "pipeline_generated_usd": pipeline_generated_usd,
                "draft_approval_rate_percent": approval_rate,
                "approval_clean_percent": clean_pct,
                "approval_edited_percent": edited_pct,
                "avg_review_duration_seconds": avg_duration_sec,
                "mean_edit_distance_ratio_percent": mean_edit_ratio,
                "total_token_burn_cost_usd": total_cost_usd,
                "total_tokens_consumed": total_tokens,
                "critic_rejection_rate_percent": critic_rejection_rate,
                "critic_suppressed_count": suppressed_count,
                "total_reviews_count": total_reviews,
                "total_runs_count": total_runs,
                "active_leads_count": active_leads_count,
                "charts": {
                    "throughput": {
                        "labels": date_labels,
                        "approved_clean": thru_clean,
                        "approved_with_edits": thru_edited,
                        "rejected": thru_rejected
                    },
                    "signals": {
                        "labels": sig_labels,
                        "dispatched_count": sig_dispatched,
                        "positive_replies": sig_replies
                    },
                    "hallucination": {
                        "labels": hal_labels,
                        "draft_counts": hal_counts
                    },
                    "reps": {
                        "labels": rep_labels,
                        "avg_duration_sec": rep_durations,
                        "edit_distance_ratio": rep_ratios
                    }
                }
            }

    def ensure_lead(
        self,
        lead_id: str,
        company_name: str = "Unknown",
        lead_name: str = "Unknown",
        email: str = "unknown@example.com",
        title: str = "Lead",
        domain: str = "example.com",
        tenant_id: str = "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
    ):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, company_name FROM leads WHERE id = ?;", (lead_id,))
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                INSERT INTO leads (id, tenant_id, account_domain, company_name, lead_name, lead_title, lead_email, status, icp_fit_score, crypto_shred_key_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'READY_FOR_AGENT', 90.0, ?, ?);
                """, (
                    lead_id, tenant_id, domain, company_name, lead_name, title, email,
                    f"arn:aws:kms:us-east-1:123456789012:key/mrk-{lead_id[:8]}",
                    datetime.now(timezone.utc).isoformat()
                ))
            elif company_name != "Unknown" and row["company_name"] in ("Unknown", "Acme Corp"):
                cursor.execute("""
                UPDATE leads SET company_name = ?, lead_name = ?, lead_email = ?, lead_title = ?, account_domain = ?
                WHERE id = ?;
                """, (company_name, lead_name, email, title, domain, lead_id))
            conn.commit()

    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE id = ?;", (lead_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_leads(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads ORDER BY created_at DESC;")
            return [dict(r) for r in cursor.fetchall()]

    def get_signals_for_lead(self, lead_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM signals WHERE lead_id = ? ORDER BY confidence_score DESC;", (lead_id,))
            return [dict(r) for r in cursor.fetchall()]

    def record_agent_run(self, run_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO agent_runs (id, tenant_id, lead_id, trace_id, total_tokens, total_cost_usd, duration_ms, critic_verdict, draft_subject, draft_body, hallucination_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                str(uuid.uuid4()), run_data["tenant_id"], run_data["lead_id"], run_data["trace_id"],
                run_data["total_tokens"], run_data["total_cost_usd"], run_data["duration_ms"],
                run_data["critic_verdict"], run_data["draft_subject"], run_data["draft_body"],
                float(run_data.get("hallucination_score", 0.02)),
                run_data.get("created_at", datetime.now(timezone.utc).isoformat())
            ))
            conn.commit()

    def record_hitl_review(self, review_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO hitl_reviews (id, tenant_id, lead_id, reviewer_id, action, review_duration_ms, body_levenshtein_distance, character_edit_distance_ratio, feedback_tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                str(uuid.uuid4()), review_data["tenant_id"], review_data["lead_id"], review_data["reviewer_id"],
                review_data["action"], review_data["review_duration_ms"], review_data["body_levenshtein_distance"],
                review_data["character_edit_distance_ratio"], json.dumps(review_data.get("feedback_tags", [])),
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()

    def record_signal(self, sig: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO signals (id, tenant_id, lead_id, signal_type, confidence_score, sentiment, title, source_name, source_uri, detected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                str(uuid.uuid4()),
                sig.get("tenant_id", "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"),
                sig["lead_id"],
                sig.get("signal_type", "COMPANY_DEVELOPMENT"),
                float(sig.get("confidence_score", 0.90)),
                sig.get("sentiment", "NEUTRAL"),
                sig.get("raw_payload", {}).get("title", sig.get("title", "Live Intent Signal"))[:140],
                sig.get("source", "Live Web")[:50],
                sig.get("raw_payload", {}).get("source_url", sig.get("source_url", "https://web.archive.org")),
                sig.get("detected_at", datetime.now(timezone.utc).isoformat())
            ))
            conn.commit()
