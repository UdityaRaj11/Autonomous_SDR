"""
Groq LLM Client & Multi-Model Resilience Module
Provides high-speed inference via Groq LPUs, dynamic model resolution,
automatic fallback cascade on 404/model_not_found, token accounting,
and dual-mode execution (Live API / Deterministic Mock Fallback).
"""

import os
import time
import random
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

try:
    from groq import AsyncGroq
    GROQ_LIBRARY_AVAILABLE = True
except ImportError:
    GROQ_LIBRARY_AVAILABLE = False

logger = logging.getLogger("sdr.llm.groq")

# Model fallback candidates in order of preference
FALLBACK_QUALITY_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "llama3-70b-8192",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "mixtral-8x7b-32768",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
    "llama3-8b-8192"
]

FALLBACK_FAST_MODELS = [
    "llama-3.1-8b-instant",
    "llama3-8b-8192",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "allam-2-7b",
    "gemma2-9b-it",
    "llama-3.2-3b-preview",
    "llama-3.2-1b-preview",
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile"
]

# Pricing per million tokens (Groq rates)
COST_PER_M_TOKENS = {
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.1-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama3-70b-8192": {"input": 0.59, "output": 0.79},
    "mixtral-8x7b-32768": {"input": 0.24, "output": 0.24},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "llama3-8b-8192": {"input": 0.05, "output": 0.08},
    "openai/gpt-oss-120b": {"input": 0.50, "output": 0.70},
    "openai/gpt-oss-20b": {"input": 0.08, "output": 0.12},
    "qwen/qwen3.8-27b": {"input": 0.20, "output": 0.30},
    "allam-2-7b": {"input": 0.05, "output": 0.08},
    "default": {"input": 0.20, "output": 0.40}
}

@dataclass
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_ms: int
    cost_usd: float
    is_mock: bool

class GroqClientService:
    def __init__(self, api_key: Optional[str] = None):
        self.resolved_quality_model: str = "llama-3.3-70b-versatile"
        self.resolved_fast_model: str = "llama-3.1-8b-instant"
        self.available_models: List[str] = []
        self.set_api_key(api_key or os.environ.get("GROQ_API_KEY"))

    def set_api_key(self, api_key: Optional[str]):
        self.api_key = api_key.strip() if api_key else None
        has_valid_key = bool(self.api_key and self.api_key.startswith("gsk_") and len(self.api_key) >= 25)
        self.is_live = bool(has_valid_key and GROQ_LIBRARY_AVAILABLE)

        if self.is_live:
            try:
                self.client = AsyncGroq(api_key=self.api_key)
                logger.info("GroqClientService configured in LIVE mode with active API key.")
            except Exception as e:
                logger.warning(f"Failed to initialize AsyncGroq: {e}. Switching to SIMULATED mode.")
                self.client = None
                self.is_live = False
        else:
            self.client = None
            logger.info("GroqClientService running in high-speed SIMULATED mode.")

    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = COST_PER_M_TOKENS.get(model, COST_PER_M_TOKENS["default"])
        input_cost = (prompt_tokens / 1_000_000.0) * rates["input"]
        output_cost = (completion_tokens / 1_000_000.0) * rates["output"]
        return round(input_cost + output_cost, 6)

    async def resolve_active_models(self) -> Dict[str, Any]:
        """Queries Groq /models to discover which models this account has access to."""
        if not self.is_live or not self.client:
            return {
                "quality": self.resolved_quality_model,
                "fast": self.resolved_fast_model,
                "all": FALLBACK_QUALITY_MODELS
            }

        try:
            model_list = await self.client.models.list()
            active_ids = [m.id for m in model_list.data]
            self.available_models = active_ids
            logger.info(f"Discovered {len(active_ids)} active Groq models: {active_ids}")

            # Resolve Quality Model
            for q in FALLBACK_QUALITY_MODELS:
                if q in active_ids:
                    self.resolved_quality_model = q
                    break

            # Resolve Fast Model
            for f in FALLBACK_FAST_MODELS:
                if f in active_ids:
                    self.resolved_fast_model = f
                    break

            # If resolved models are still not in active_ids, select from any active chat-capable model
            chat_capable = [
                m for m in active_ids 
                if not any(k in m.lower() for k in ["whisper", "orpheus", "prompt-guard", "safeguard", "embed"])
            ]
            if self.resolved_quality_model not in active_ids and chat_capable:
                self.resolved_quality_model = chat_capable[0]
            if self.resolved_fast_model not in active_ids and chat_capable:
                self.resolved_fast_model = chat_capable[-1]

            logger.info(f"Resolved models -> Quality: {self.resolved_quality_model}, Fast: {self.resolved_fast_model}")
            return {
                "quality": self.resolved_quality_model,
                "fast": self.resolved_fast_model,
                "all": active_ids
            }
        except Exception as e:
            logger.warning(f"Failed to query Groq models list: {e}")
            return {
                "quality": self.resolved_quality_model,
                "fast": self.resolved_fast_model,
                "all": []
            }

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.2,
        max_tokens: int = 1024,
        json_mode: bool = False,
        max_retries: int = 2
    ) -> LLMResponse:
        start_time = time.perf_counter()

        if not self.is_live or not self.client:
            # Deterministic Simulated Execution
            await asyncio.sleep(0.20)
            content = self._generate_mock_response(messages, json_mode)
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            p_tokens = sum(len(m.get("content", "").split()) * 2 for m in messages)
            c_tokens = len(content.split()) * 2
            cost = self.calculate_cost(model, p_tokens, c_tokens)
            return LLMResponse(
                content=content,
                model=f"{model}-simulated",
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=p_tokens + c_tokens,
                duration_ms=duration_ms,
                cost_usd=cost,
                is_mock=True
            )

        # Build candidate list with requested model first, then fallback alternatives
        candidate_models = [model]
        if "70b" in model or "120b" in model or "quality" in model:
            for m in FALLBACK_QUALITY_MODELS:
                if m not in candidate_models:
                    candidate_models.append(m)
        else:
            for m in FALLBACK_FAST_MODELS:
                if m not in candidate_models:
                    candidate_models.append(m)

        # Prioritize models known to be available in this Groq tenant
        if self.available_models:
            valid_available = [
                m for m in self.available_models 
                if not any(k in m.lower() for k in ["whisper", "orpheus", "prompt-guard", "safeguard"])
            ]
            prioritized = [m for m in candidate_models if m in valid_available]
            remainder = [m for m in candidate_models if m not in valid_available]
            candidate_models = prioritized + remainder

        for current_model in candidate_models:
            attempt = 0
            model_404_error = False

            while attempt < max_retries:
                try:
                    kwargs = {
                        "model": current_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                    if json_mode:
                        kwargs["response_format"] = {"type": "json_object"}

                    response = await self.client.chat.completions.create(**kwargs)
                    duration_ms = int((time.perf_counter() - start_time) * 1000)
                    content = response.choices[0].message.content or ""
                    usage = response.usage
                    p_tokens = usage.prompt_tokens if usage else 500
                    c_tokens = usage.completion_tokens if usage else 200
                    cost = self.calculate_cost(current_model, p_tokens, c_tokens)

                    # Update successful model pointer
                    if "70b" in current_model:
                        self.resolved_quality_model = current_model
                    else:
                        self.resolved_fast_model = current_model

                    return LLMResponse(
                        content=content,
                        model=current_model,
                        prompt_tokens=p_tokens,
                        completion_tokens=c_tokens,
                        total_tokens=p_tokens + c_tokens,
                        duration_ms=duration_ms,
                        cost_usd=cost,
                        is_mock=False
                    )
                except Exception as e:
                    err_msg = str(e).lower()

                    # 1. 401 Unauthorized -> Invalid API Key (Fast fail to simulated mode, DO NOT RETRY)
                    if "401" in err_msg or "auth" in err_msg or "invalid api key" in err_msg:
                        logger.warning(f"Groq API authentication rejected (401). Switching to high-speed SIMULATED mode.")
                        self.is_live = False
                        break

                    # 2. 404 Model Not Found / Access Denied -> DO NOT RETRY! Immediately switch candidate model!
                    if "404" in err_msg or "model_not_found" in err_msg or "does not exist or you do not have access" in err_msg:
                        logger.warning(f"Groq model `{current_model}` not available (404). Cascading to next fallback candidate...")
                        model_404_error = True
                        break

                    # 3. 429 Rate Limit or 5xx Server Error -> Exponential Backoff
                    attempt += 1
                    if attempt >= max_retries:
                        break
                    base_delay = 1.0 * (2 ** attempt)
                    sleep_duration = random.uniform(0.5, min(3.0, base_delay))
                    logger.warning(f"Groq API transient error on `{current_model}` (attempt {attempt}/{max_retries}): {e}. Retrying in {sleep_duration:.2f}s...")
                    await asyncio.sleep(sleep_duration)

            if not self.is_live:
                break
            if not model_404_error:
                # If the error was not a 404 (e.g. fatal payload or rate limit exhausted), exit candidate loop
                break

        logger.info("Executing via deterministic high-speed output generator.")
        fallback_content = self._generate_mock_response(messages, json_mode)
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return LLMResponse(
            content=fallback_content,
            model=f"{model}-fallback",
            prompt_tokens=600,
            completion_tokens=250,
            total_tokens=850,
            duration_ms=duration_ms,
            cost_usd=0.001,
            is_mock=True
        )

    def _generate_mock_response(self, messages: List[Dict[str, str]], json_mode: bool) -> str:
        last_msg = messages[-1]["content"].lower() if messages else ""
        
        # Check Node 4: Critic
        if "node 4" in last_msg or "critic" in last_msg:
            return '{"verdict": "PASSED", "hallucination_score": 0.02, "spam_score": 0.04, "readability_grade": "Grade 8.2", "risk_tags": [], "critique_notes": "All claims grounded in retrieved collateral. Tone is objective and consultative."}' if json_mode else "Verdict: PASSED"

        # Check Node 2: Rank
        if "node 2" in last_msg or "rank request" in last_msg or "icp_fit_score" in last_msg:
            return '{"selected_signal_type": "HIRING_EXPANSION", "icp_fit_score": 94.0, "ranking_rationale": "Cloud Security Architect hiring correlates directly with audit preparation drag", "negative_news_risk": false}' if json_mode else "Ranked Signal: HIRING_EXPANSION (Score: 94.0)"

        # Check Node 1: Extract
        if "node 1" in last_msg or "extract request" in last_msg:
            return '{"pain_points": ["Manual audit evidence aggregation drag", "Engineering capacity loss during audit sprints"], "buying_persona": "VP Platform Engineering / Cloud Architecture", "strategic_priorities": ["Automated telemetry compliance", "Multi-region scaling"]}' if json_mode else "Pain Points: Manual audit aggregation drag; Persona: Platform Engineering"

        # Default Node 3: Draft
        if json_mode:
            return '{"subject": "Automating continuous SOC 2 evidence collection for Q1 expansion", "body": "Hi,\\n\\nNoticed your team is scaling Cloud Security openings to support platform expansion.\\n\\nWhen scaling payments infrastructure under strict audit deadlines, manual evidence aggregation often creates heavy engineering drag. We helped peers reduce continuous audit prep by 78% using automated telemetry verification.\\n\\nWould you be open to comparing benchmarks next Tuesday at 10:00 AM?\\n\\nBest,\\nSarah Jenkins", "channel": "EMAIL_SEQUENCE_STEP_1"}'
        
        return "Automating continuous audit evidence collection for platform expansion."
