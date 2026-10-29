"""
HITL & Levenshtein Diff Calculation Engine
Provides character-level Levenshtein distance metrics, edit distance ratios,
Word Error Rate (WER), and structured diff chunk generation.
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

@dataclass
class DiffMetrics:
    original_char_count: int
    final_char_count: int
    subject_levenshtein_distance: int
    body_levenshtein_distance: int
    character_edit_distance_ratio: float
    word_error_rate: float
    is_modified: bool

@dataclass
class DiffChunk:
    operation: str  # EQUAL | INSERT | DELETE
    text: str

class HITLDiffEngine:
    @staticmethod
    def compute_levenshtein(s1: str, s2: str) -> int:
        if s1 == s2:
            return 0
        m, n = len(s1), len(s2)
        if m == 0:
            return n
        if n == 0:
            return m

        # Matrix initialization
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i - 1] == s2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

        return dp[m][n]

    @classmethod
    def compute_metrics(
        cls,
        orig_subject: str,
        final_subject: str,
        orig_body: str,
        final_body: str
    ) -> DiffMetrics:
        subj_dist = cls.compute_levenshtein(orig_subject, final_subject)
        body_dist = cls.compute_levenshtein(orig_body, final_body)

        orig_len = len(orig_body)
        ratio = (body_dist / max(1, orig_len)) * 100.0 if orig_len > 0 else 0.0

        # Word Error Rate approximation
        orig_words = orig_body.strip().split()
        final_words = final_body.strip().split()
        word_dist = cls.compute_levenshtein(" ".join(orig_words), " ".join(final_words))
        wer = (word_dist / max(1, len(" ".join(orig_words)))) * 100.0 if orig_words else 0.0

        is_mod = (subj_dist > 0 or body_dist > 0)

        return DiffMetrics(
            original_char_count=orig_len,
            final_char_count=len(final_body),
            subject_levenshtein_distance=subj_dist,
            body_levenshtein_distance=body_dist,
            character_edit_distance_ratio=round(ratio, 2),
            word_error_rate=round(wer, 2),
            is_modified=is_mod
        )

    @classmethod
    def generate_diff_chunks(cls, orig_text: str, final_text: str) -> List[Dict[str, str]]:
        """Simple chunk diff generator for audit records."""
        if orig_text == final_text:
            return [{"operation": "EQUAL", "text": orig_text}]
        
        # When modified, record before & after
        return [
            {"operation": "DELETE", "text": orig_text},
            {"operation": "INSERT", "text": final_text}
        ]
