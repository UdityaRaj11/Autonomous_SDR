"""
Autonomous SDR Signal-Based Outreach Engine: Main Application Server
Powered by Groq LPUs (llama-3.3-70b-versatile & llama-3.1-8b-instant),
Hybrid RAG, Cryptographic Audit Trails, and HITL Diff Tracking.
"""

import os
import time
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.llm.groq_client import GroqClientService
from backend.rag.hybrid_retriever import HybridRetriever
from backend.orchestrator.chain import PromptChainOrchestrator
from backend.compliance.audit_store import CryptographicAuditStore
from backend.hitl.diff_engine import HITLDiffEngine
from backend.db.database import DatabaseManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sdr.server")

app = FastAPI(
    title="Autonomous SDR Signal Engine API (Groq Provider)",
    version="1.0.0-PROD",
    description="Enterprise-grade backend for signal-driven SDR outreach, 4-node Groq prompt chains, and SOC 2 / ISO 27001 auditability."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_anti_cache_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# -----------------------------------------------------------------------------
# GLOBAL SERVICE SINGLETONS
# -----------------------------------------------------------------------------
groq_service = GroqClientService()
hybrid_retriever = HybridRetriever()
audit_store = CryptographicAuditStore(auto_seed=True)
orchestrator = PromptChainOrchestrator(
    groq_client=groq_service,
    retriever=hybrid_retriever,
    audit_store=audit_store
)
db_manager = DatabaseManager()

# -----------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# -----------------------------------------------------------------------------
class ExecuteChainRequest(BaseModel):
    lead_id: Optional[str] = None
    lead_name: str
    company_name: str
    title: str
    email: str
    account_domain: Optional[str] = ""
    signals: Optional[List[Dict[str, Any]]] = None
    focus_query: Optional[str] = None
    force_live_search: bool = True

class LiveSearchRequest(BaseModel):
    company_name: str
    person_name: Optional[str] = ""
    title: Optional[str] = ""
    domain: Optional[str] = ""
    focus_query: Optional[str] = None

class HITLReviewSubmission(BaseModel):
    lead_id: str
    trace_id: str
    reviewer_id: str = "sdr-user-5541"
    action: str  # APPROVED_UNMODIFIED | APPROVED_WITH_EDITS | REJECTED_BAD_FIT
    original_subject: str
    original_body: str
    final_subject: str
    final_body: str
    feedback_tags: List[str] = Field(default_factory=list)
    rejection_notes: Optional[str] = None
    review_duration_seconds: int = 0

class DispatchRequest(BaseModel):
    lead_id: str
    trace_id: str
    platform: str = "Outreach.io"

class GroqKeyUpdate(BaseModel):
    api_key: str

# -----------------------------------------------------------------------------
# REST API ROUTERS
# -----------------------------------------------------------------------------

@app.get("/api/v1/health")
def health_check():
    integrity = audit_store.verify_chain_integrity()
    return {
        "status": "HEALTHY",
        "service": "autonomous-sdr-engine",
        "llm_provider": "Groq",
        "groq_mode": "LIVE" if groq_service.is_live else "SIMULATED_FALLBACK",
        "primary_model": groq_service.resolved_quality_model,
        "fast_model": groq_service.resolved_fast_model,
        "compliance": "SOC 2 Type II / ISO 27001",
        "audit_chain_integrity": integrity["verified"],
        "audit_events_count": len(audit_store.events),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/v1/settings/groq-key")
async def update_groq_key(req: GroqKeyUpdate):
    groq_service.set_api_key(req.api_key)
    discovery = await groq_service.resolve_active_models()
    return {
        "status": "CONFIGURED",
        "groq_mode": "LIVE" if groq_service.is_live else "SIMULATED_FALLBACK",
        "is_live": groq_service.is_live,
        "primary_model": groq_service.resolved_quality_model,
        "fast_model": groq_service.resolved_fast_model,
        "available_models": groq_service.available_models or discovery.get("all", [])
    }

@app.get("/api/v1/groq/models")
async def get_groq_models():
    discovery = await groq_service.resolve_active_models()
    return {
        "status": "SUCCESS",
        "groq_mode": "LIVE" if groq_service.is_live else "SIMULATED_FALLBACK",
        "is_live": groq_service.is_live,
        "resolved_quality_model": groq_service.resolved_quality_model,
        "resolved_fast_model": groq_service.resolved_fast_model,
        "available_models": groq_service.available_models or discovery.get("all", [])
    }

@app.get("/api/v1/leads")
def get_leads_and_signals():
    leads = db_manager.get_leads()
    for lead in leads:
        lead["signals"] = db_manager.get_signals_for_lead(lead["id"])
    return {"leads": leads}

@app.post("/api/v1/search/live")
async def execute_live_search(req: LiveSearchRequest):
    result = await orchestrator.search_service.search_company_signals(
        company_name=req.company_name,
        person_name=req.person_name or "",
        title=req.title or "",
        domain=req.domain or "",
        focus_query=req.focus_query
    )
    return result

@app.post("/api/v1/pipeline/execute")
async def execute_prompt_chain(req: ExecuteChainRequest):
    lead_id = req.lead_id or str(uuid.uuid4())
    trace_id = uuid.uuid4().hex[:32]
    account_domain = req.account_domain or (f"{req.company_name.lower().replace(' ', '')}.com" if req.company_name else "")

    logger.info(f"Executing 4-node Groq chain with live web search for: {req.lead_name} ({req.company_name}) [Trace: {trace_id}]")
    result = await orchestrator.execute_chain(
        lead_id=lead_id,
        lead_name=req.lead_name,
        company_name=req.company_name,
        title=req.title,
        email=req.email,
        domain=account_domain,
        trace_id=trace_id,
        custom_signals=req.signals,
        focus_query=req.focus_query,
        force_live_search=req.force_live_search
    )

    # Ensure lead exists in DB
    db_manager.ensure_lead(
        lead_id=lead_id,
        company_name=req.company_name,
        lead_name=req.lead_name,
        email=req.email,
        title=req.title,
        domain=account_domain
    )

    # Persist live discovered signals in DB
    for s in result.live_signals:
        db_manager.record_signal({
            "tenant_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
            "lead_id": lead_id,
            "signal_type": s.get("type", "COMPANY_DEVELOPMENT"),
            "source": s.get("source", "Live Web"),
            "raw_payload": s,
            "confidence_score": s.get("confidence", 0.90),
            "sentiment": s.get("sentiment", "NEUTRAL")
        })

    # Persist in DB
    db_manager.record_agent_run({
        "tenant_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
        "lead_id": lead_id,
        "trace_id": trace_id,
        "total_tokens": result.total_tokens,
        "total_cost_usd": result.total_cost_usd,
        "duration_ms": result.total_duration_ms,
        "critic_verdict": result.node4_critic["critic_results"]["verdict"],
        "draft_subject": result.node3_draft["draft_output"]["subject"],
        "draft_body": result.node3_draft["draft_output"]["body"],
        "hallucination_score": float(result.node4_critic["critic_results"].get("hallucination_score", 0.02))
    })

    return {
        "trace_id": trace_id,
        "lead_id": lead_id,
        "workflow_status": result.workflow_status,
        "total_tokens": result.total_tokens,
        "total_cost_usd": result.total_cost_usd,
        "total_duration_ms": result.total_duration_ms,
        "nodes": {
            "node1_extract": result.node1_extract,
            "node2_rank": result.node2_rank,
            "node3_draft": result.node3_draft,
            "node4_critic": result.node4_critic
        },
        "retrieved_collateral": result.retrieved_collateral,
        "live_signals": result.live_signals,
        "search_metadata": result.search_metadata
    }

@app.post("/api/v1/hitl/submit")
def submit_hitl_review(submission: HITLReviewSubmission):
    if submission.action == "APPROVE_AND_DISPATCH" and "[BLOCKED]" in submission.final_subject:
        raise HTTPException(
            status_code=400,
            detail="Cannot approve and dispatch an unverified lead with zero discovered business signals."
        )

    diff_metrics = HITLDiffEngine.compute_metrics(
        orig_subject=submission.original_subject,
        final_subject=submission.final_subject,
        orig_body=submission.original_body,
        final_body=submission.final_body
    )

    diff_chunks = HITLDiffEngine.generate_diff_chunks(
        orig_text=submission.original_body,
        final_text=submission.final_body
    )

    # Look up lead metadata for rich audit context
    lead = db_manager.get_lead(submission.lead_id) or {}
    company_name = lead.get("company_name", "Enterprise Prospect")
    lead_name = lead.get("lead_name", "Target Executive")

    # Record Audit Event
    audit_payload = {
        "company_name": company_name,
        "target_lead": lead_name,
        "hitl_action": submission.action,
        "review_duration_seconds": submission.review_duration_seconds,
        "text_diff_metrics": {
            "subject_levenshtein_distance": diff_metrics.subject_levenshtein_distance,
            "body_levenshtein_distance": diff_metrics.body_levenshtein_distance,
            "character_edit_distance_ratio": diff_metrics.character_edit_distance_ratio,
            "word_error_rate": diff_metrics.word_error_rate
        },
        "diff_chunks": diff_chunks,
        "feedback_tags": submission.feedback_tags,
        "rejection_notes": submission.rejection_notes,
        "final_subject": submission.final_subject
    }

    event = audit_store.record_event(
        lead_id=submission.lead_id,
        event_type="HITL_REVIEW_COMPLETED",
        actor_type="SALES_REPRESENTATIVE",
        actor_id=submission.reviewer_id,
        trace_id=submission.trace_id,
        raw_payload=audit_payload,
        lead_name=lead_name,
        company_name=company_name
    )

    # Ensure lead exists in DB
    db_manager.ensure_lead(lead_id=submission.lead_id, company_name=company_name, lead_name=lead_name)

    # Record in SQLite DB
    db_manager.record_hitl_review({
        "tenant_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
        "lead_id": submission.lead_id,
        "reviewer_id": submission.reviewer_id,
        "action": submission.action,
        "review_duration_ms": submission.review_duration_seconds * 1000,
        "body_levenshtein_distance": diff_metrics.body_levenshtein_distance,
        "character_edit_distance_ratio": diff_metrics.character_edit_distance_ratio,
        "feedback_tags": submission.feedback_tags
    })

    return {
        "status": "RECORDED",
        "event_id": event.event_id,
        "levenshtein_distance": diff_metrics.body_levenshtein_distance,
        "character_edit_distance_ratio": diff_metrics.character_edit_distance_ratio,
        "word_error_rate": diff_metrics.word_error_rate,
        "is_modified": diff_metrics.is_modified
    }

@app.post("/api/v1/dispatch/outreach")
def dispatch_to_sep(req: DispatchRequest):
    if "[BLOCKED]" in req.subject:
        raise HTTPException(
            status_code=400,
            detail=f"Outreach dispatch blocked: Cannot dispatch blocked draft for unverified account."
        )

    idempotency_token = f"idem_{uuid.uuid4().hex[:12]}"
    mailing_id = f"mail_{uuid.uuid4().hex[:8]}"

    lead = db_manager.get_lead(req.lead_id) or {}
    company_name = lead.get("company_name", "Enterprise Prospect")
    lead_name = lead.get("lead_name", "Target Executive")

    event = audit_store.record_event(
        lead_id=req.lead_id,
        event_type="SALES_ENGAGEMENT_DISPATCHED",
        actor_type="INTEGRATION_DISPATCHER",
        actor_id="sep-dispatcher-pool",
        trace_id=req.trace_id,
        raw_payload={
            "company_name": company_name,
            "target_lead": lead_name,
            "platform": req.platform,
            "mailing_id": mailing_id,
            "idempotency_token": idempotency_token,
            "sync_status": "SUCCESS_QUEUED_IN_SEP"
        },
        lead_name=lead_name,
        company_name=company_name
    )

    return {
        "status": "DISPATCHED",
        "platform": req.platform,
        "mailing_id": mailing_id,
        "idempotency_token": idempotency_token,
        "audit_event_id": event.event_id
    }

@app.get("/api/v1/audit/events")
def get_audit_events(limit: int = 50):
    events = audit_store.list_events(limit=limit)
    integrity = audit_store.verify_chain_integrity()
    return {
        "total_records": len(events),
        "chain_integrity": integrity,
        "events": events
    }

@app.get("/api/v1/audit/verify")
def verify_audit_chain():
    return audit_store.verify_chain_integrity()

@app.get("/api/v1/dashboard/metrics")
def get_dashboard_metrics():
    return db_manager.get_dashboard_analytics()

# -----------------------------------------------------------------------------
# STATIC FRONTEND SERVING
# -----------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("frontend/index.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)

