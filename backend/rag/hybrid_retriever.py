"""
Hybrid RAG & Collateral Retrieval Subsystem
Combines dense semantic vector scoring with sparse BM25 lexical search
using Reciprocal Rank Fusion (RRF k=60).
"""

import math
import re
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class CollateralChunk:
    chunk_id: str
    doc_title: str
    category: str
    content: str
    dense_vector: List[float]

@dataclass
class RetrievedChunkResult:
    chunk_id: str
    doc_title: str
    category: str
    content: str
    dense_score: float
    bm25_score: float
    rrf_score: float
    final_rank: int

class HybridRetriever:
    def __init__(self):
        self.chunks: List[CollateralChunk] = self._seed_enterprise_collateral()
        self.doc_freqs: Dict[str, int] = {}
        self.avg_doc_len: float = 0.0
        self._build_bm25_index()

    def _seed_enterprise_collateral(self) -> List[CollateralChunk]:
        return [
            CollateralChunk(
                chunk_id="chunk-case-acme-bank",
                doc_title="Acme Global Bank: Multi-Region SOC 2 Type II Telemetry Case Study",
                category="CASE_STUDY",
                content=(
                    "Acme Bank migrated core payment processing to AWS EKS and distributed PostgreSQL. "
                    "During peak quarterly audits, engineering teams spent 140+ hours manually screenshotting and verifying "
                    "audit evidence across regions. By implementing continuous telemetry verification and cryptographic audit "
                    "chains, Acme reduced compliance prep time by 78%, eliminating all auditor clarification cycles."
                ),
                dense_vector=[0.12, 0.45, 0.88, 0.23, 0.54]
            ),
            CollateralChunk(
                chunk_id="chunk-battlecard-continuous-audit",
                doc_title="Continuous Compliance & Tamper-Proof Audit Battlecard",
                category="BATTLECARD",
                content=(
                    "Competitive positioning against manual GRC tools: Legacy platforms like Vanta and Drata rely on periodic API "
                    "polling that misses real-time drift. Our engine embeds cryptographic SHA-256 hash chaining directly into "
                    "event streaming pipelines, providing instant mathematical proof of non-tampering and sub-second verification."
                ),
                dense_vector=[0.08, 0.52, 0.74, 0.31, 0.62]
            ),
            CollateralChunk(
                chunk_id="chunk-case-neopay-fintech",
                doc_title="NeoPay European Ledger: High-Throughput PSD2 Audit Architecture",
                category="CASE_STUDY",
                content=(
                    "European financial platform NeoPay required zero-downtime evidence collection while processing 8,000 TPS. "
                    "Using event-sourced audit logs with AWS KMS crypto-shredding for GDPR Article 17 compliance, they passed their "
                    "European Banking Authority (EBA) security review with zero non-conformances."
                ),
                dense_vector=[0.15, 0.61, 0.92, 0.19, 0.48]
            ),
            CollateralChunk(
                chunk_id="chunk-whitepaper-crypto-shred",
                doc_title="Enterprise Data Privacy & Cryptographic Shredding Whitepaper",
                category="WHITEPAPER",
                content=(
                    "How to satisfy GDPR Right to be Forgotten inside append-only, immutable WORM audit logs: Assigning a per-subject "
                    "KMS key alias allows permanent cryptographic erasure of surrogate PII tokens upon deletion requests, while "
                    "preserving the structural and mathematical integrity of the immutable audit trail."
                ),
                dense_vector=[0.04, 0.38, 0.65, 0.45, 0.71]
            )
        ]

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())

    def _build_bm25_index(self):
        total_len = 0
        for chunk in self.chunks:
            tokens = set(self._tokenize(chunk.content))
            total_len += len(self._tokenize(chunk.content))
            for t in tokens:
                self.doc_freqs[t] = self.doc_freqs.get(t, 0) + 1
        self.avg_doc_len = total_len / max(1, len(self.chunks))

    def _compute_bm25(self, query_tokens: List[str], chunk_content: str, k1: float = 1.5, b: float = 0.75) -> float:
        doc_tokens = self._tokenize(chunk_content)
        doc_len = len(doc_tokens)
        score = 0.0
        n_docs = len(self.chunks)

        for token in query_tokens:
            if token not in self.doc_freqs:
                continue
            df = self.doc_freqs[token]
            idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
            tf = doc_tokens.count(token)
            denom = tf + k1 * (1.0 - b + b * (doc_len / max(1.0, self.avg_doc_len)))
            score += idf * ((tf * (k1 + 1.0)) / max(0.001, denom))
        return round(score, 3)

    def _compute_dense_similarity(self, query: str, chunk: CollateralChunk) -> float:
        # Deterministic semantic alignment simulation
        query_words = set(self._tokenize(query))
        content_words = set(self._tokenize(chunk.content))
        overlap = len(query_words.intersection(content_words))
        base_sim = min(0.95, 0.60 + (overlap * 0.05))
        return round(base_sim, 3)

    def retrieve(self, query: str, top_k: int = 3) -> List[RetrievedChunkResult]:
        query_tokens = self._tokenize(query)

        # 1. Compute scores
        scored_dense = []
        scored_bm25 = []
        for chunk in self.chunks:
            d_score = self._compute_dense_similarity(query, chunk)
            b_score = self._compute_bm25(query_tokens, chunk.content)
            scored_dense.append((chunk, d_score))
            scored_bm25.append((chunk, b_score))

        # 2. Sort ranks
        scored_dense.sort(key=lambda x: x[1], reverse=True)
        scored_bm25.sort(key=lambda x: x[1], reverse=True)

        dense_ranks = {item[0].chunk_id: rank + 1 for rank, item in enumerate(scored_dense)}
        bm25_ranks = {item[0].chunk_id: rank + 1 for rank, item in enumerate(scored_bm25)}

        # 3. Reciprocal Rank Fusion (RRF k=60)
        rrf_results = []
        k_smooth = 60.0
        for chunk in self.chunks:
            r_dense = dense_ranks[chunk.chunk_id]
            r_bm25 = bm25_ranks[chunk.chunk_id]
            rrf_score = (1.0 / (k_smooth + r_dense)) + (1.0 / (k_smooth + r_bm25))

            # Retrieve scores
            d_val = next(s[1] for s in scored_dense if s[0].chunk_id == chunk.chunk_id)
            b_val = next(s[1] for s in scored_bm25 if s[0].chunk_id == chunk.chunk_id)

            rrf_results.append({
                "chunk": chunk,
                "dense_score": d_val,
                "bm25_score": b_val,
                "rrf_score": rrf_score
            })

        # 4. Sort by RRF
        rrf_results.sort(key=lambda x: x["rrf_score"], reverse=True)

        final_output = []
        for rank, res in enumerate(rrf_results[:top_k], start=1):
            c = res["chunk"]
            final_output.append(RetrievedChunkResult(
                chunk_id=c.chunk_id,
                doc_title=c.doc_title,
                category=c.category,
                content=c.content,
                dense_score=res["dense_score"],
                bm25_score=res["bm25_score"],
                rrf_score=round(res["rrf_score"], 5),
                final_rank=rank
            ))
        return final_output
