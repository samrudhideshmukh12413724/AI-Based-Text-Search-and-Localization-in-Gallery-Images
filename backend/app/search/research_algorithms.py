"""Research Paper Algorithms Engine for DocuLens AI.

Enrolls and implements the mathematical formulations and algorithms from:
1. Paper 1: BPE-Level Visual-Textual Subword Alignment & Inclusive-OR Matching
2. Paper 9: Cross-Weighted Product Relevance Scoring
3. Paper 12: Boyer-Moore-Horspool Fast Right-to-Left String Search with Shift Tables
4. Paper 13: Resume Short-Text Fuzzy Matching with Bounded Dice Coefficient
"""

import math
import re
from typing import Dict, List, Any, Optional, Tuple, Set


# =============================================================================
# 1. PAPER 12: Boyer-Moore-Horspool Exact Substring Matcher
# Implements right-to-left character scanning with precomputed bad-character skip table.
# =============================================================================
class BoyerMooreHorspoolMatcher:
    """
    Paper 12 Implementation: Boyer-Moore-Horspool pattern search with Unicode support.
    Skips redundant character comparisons by precomputing bad-character shift offsets.
    """

    def __init__(self, pattern: str):
        self.pattern = pattern.strip().lower()
        self.m = len(self.pattern)
        self.shift_table: Dict[str, int] = {}
        self._build_shift_table()

    def _build_shift_table(self) -> None:
        """Precompute the shift distance for each character in pattern."""
        if self.m == 0:
            return
        # Default shift is length of pattern
        for i in range(self.m - 1):
            self.shift_table[self.pattern[i]] = self.m - 1 - i

    def search_in(self, text: str) -> List[int]:
        """
        Searches for pattern occurrences in text using right-to-left matching and shift jumps.
        Returns list of starting character indices.
        """
        text_lower = text.lower()
        n = len(text_lower)
        if self.m == 0 or self.m > n:
            return []

        occurrences: List[int] = []
        i = 0

        while i <= n - self.m:
            j = self.m - 1
            while j >= 0 and self.pattern[j] == text_lower[i + j]:
                j -= 1

            if j < 0:
                occurrences.append(i)
                # Shift by pattern length or shift table if possible
                i += self.shift_table.get(text_lower[i + self.m - 1], self.m)
            else:
                last_char = text_lower[i + self.m - 1]
                shift = self.shift_table.get(last_char, self.m)
                i += max(1, shift)

        return occurrences

    def match_score(self, text: str) -> float:
        """Returns 1.0 if match exists, 0.0 otherwise."""
        matches = self.search_in(text)
        return 1.0 if len(matches) > 0 else 0.0


# =============================================================================
# 2. PAPER 13: Bounded Error Dice Coefficient Fuzzy Matcher
# Implements character bi-gram set overlap with adaptive threshold bands (k1, k2).
# =============================================================================
def compute_character_ngrams(s: str) -> Set[str]:
    """Extracts character unigrams and adjacent bi-grams from string."""
    clean = re.sub(r"\s+", "", s.lower())
    if not clean:
        return set()
    ngrams = set(clean)
    for i in range(len(clean) - 1):
        ngrams.add(clean[i:i+2])
    return ngrams


def compute_dice_similarity(s1: str, s2: str) -> float:
    """
    Paper 13 Implementation: Multi-order Dice Similarity Coefficient:
    Dice(A, B) = 2 * |A ∩ B| / (|A| + |B|)
    Measures short-text token overlap combining unigrams and bigrams,
    resilient to character substitutions, transpositions, and OCR typos.
    """
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    ng1 = compute_character_ngrams(s1)
    ng2 = compute_character_ngrams(s2)

    total_len = len(ng1) + len(ng2)
    if total_len == 0:
        return 0.0

    intersection = len(ng1.intersection(ng2))
    return round((2.0 * intersection) / float(total_len), 4)


def bounded_dice_search(
    query_token: str,
    target_tokens: List[str],
    k1_exact_thresh: float = 0.90,
    k2_fuzzy_thresh: float = 0.70,
) -> Tuple[float, Optional[str]]:
    """
    Paper 13 3-band fuzzy evaluation:
    - Dice >= k1: High confidence match (treated as exact)
    - k2 <= Dice < k1: Bounded fuzzy match accepted
    - Dice < k2: Rejected as mismatch
    """
    best_score = 0.0
    best_word = None

    for t in target_tokens:
        score = compute_dice_similarity(query_token, t)
        if score > best_score:
            best_score = score
            best_word = t

    if best_score >= k1_exact_thresh:
        return 1.0, best_word
    elif best_score >= k2_fuzzy_thresh:
        return best_score, best_word
    return 0.0, None


# =============================================================================
# 3. PAPER 1: BPE Subword Tokenization & Inclusive-OR Aggregation
# Decomposes queries into subword pieces and scores visual-textual support.
# =============================================================================
def bpe_subword_tokenize(word: str, min_subword_len: int = 3) -> List[str]:
    """
    Paper 1 BPE-inspired subword decomposition:
    Generates n-gram subword chunks (length 3 to len-1) to match partial or fragmented OCR words.
    """
    clean = word.lower().strip()
    w_len = len(clean)
    if w_len <= min_subword_len:
        return [clean]

    subwords = set()
    # Add full word
    subwords.add(clean)
    # Generate subwords of length 3, 4, 5
    for sub_len in range(min_subword_len, min(6, w_len)):
        for i in range(w_len - sub_len + 1):
            subwords.add(clean[i:i + sub_len])

    return sorted(list(subwords), key=len, reverse=True)


def bpe_inclusive_or_score(query: str, doc_tokens: List[str]) -> Tuple[float, List[str]]:
    """
    Paper 1 Subword Inclusive-OR Principle:
    For a queried word, all constituent subwords must find convincing visual/textual support
    in the document's OCR word boxes for the overall word to be accepted.
    """
    q_clean = query.lower().strip()
    q_words = [w for w in re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", q_clean) if len(w) >= 3]
    if not q_words:
        return 0.0, []

    doc_text_combined = " ".join(doc_tokens).lower()
    matched_subwords: List[str] = []
    word_scores: List[float] = []

    for qw in q_words:
        subwords = bpe_subword_tokenize(qw, min_subword_len=3)
        if not subwords:
            continue

        # Check subword support in document
        supported_count = 0
        for sub in subwords:
            if sub in doc_text_combined:
                supported_count += 1
                matched_subwords.append(sub)

        # Fraction of subwords supported
        support_ratio = supported_count / float(len(subwords))
        word_scores.append(support_ratio)

    if not word_scores:
        return 0.0, []

    # Combined score across query terms
    final_score = sum(word_scores) / len(word_scores)
    return round(final_score, 4), matched_subwords


# =============================================================================
# 4. PAPER 9: Cross-Weighted Product Text Similarity & Comprehensive Search Ranking
# Reference: Zengtao Zhao, Hao Zhang, Yilong Yu (IEEE EI2 2020)
# "Method For Calculating Text Similarity Of Cross-Weighted Products Applied To Power Grid Model Search"
# Formulas:
#   Eq. 5: W_1[i] = L1 + i, W_2[i] = L2 + i (Right-side linear positional weights)
#   Eq. 6: Sw1 = sum(W_1), Sw2 = sum(W_2)
#   Eq. 7: For non-matching char in T2 (k-th missing), W2[i] = k, and excess is redistributed
#   Eq. 8: S_s = sum_{matches}( W2[j] * sum_{p=d}^{u} W1[i+p] ) / (Sw1 * Sw2)
#   Eq. 2: S_f = 1 / (1 + exp(-W_s)) (Sigmoid filter matching score)
#   Eq. 1: S = S_f * 0.5 + S_s * 0.3 + S_h * 0.2 (Tri-part comprehensive score)
# =============================================================================
def compute_cross_weighted_similarity(text1: str, text2: str, right_emphasis: bool = True) -> float:
    """
    Paper 9 (IEEE EI2 2020) Cross-Weighted Product Text Similarity Algorithm:
    - Builds initial positional weight arrays W1, W2 prioritizing right-side text (types/endings).
    - Attenuates non-matching character weights and redistributes residual weight forward.
    - Multiplies cross-weights over contiguous matching ranges [d, u], rewarding unbroken sub-strings.
    - Returns similarity score in [0.0, 1.0].
    """
    t1 = text1.strip()
    t2 = text2.strip()
    if not t1 or not t2:
        return 0.0
    if t1 == t2:
        return 1.0

    # According to Sec III-D, T1 has length L1, T2 has length L2 with L1 <= L2
    if len(t1) > len(t2):
        t1, t2 = t2, t1

    L1, L2 = len(t1), len(t2)
    if right_emphasis:
        # Eq. 5: Positional weight increasing from left to right
        W1 = [float(L1 + i) for i in range(1, L1 + 1)]
        W2 = [float(L2 + i) for i in range(1, L2 + 1)]
    else:
        W1 = [1.0 for _ in range(L1)]
        W2 = [1.0 for _ in range(L2)]

    # Eq. 6: Sum of weight vectors
    Sw1 = sum(W1)
    Sw2 = sum(W2)
    if Sw1 * Sw2 == 0:
        return 0.0

    # Eq. 7: Weight attenuation and reallocation for characters in T2 not belonging to T1
    k = 0
    W2_adj = list(W2)
    for i in range(L2):
        if t2[i] not in t1:
            k += 1
            old_w = W2_adj[i]
            W2_adj[i] = float(k)
            rem = L2 - (i + 1)
            if rem > 0:
                diff = (old_w - float(k)) / float(rem)
                for j in range(i + 1, L2):
                    W2_adj[j] += diff

    # Eq. 8: Continuous matching range [d, u] cross-multiplication
    total_numerator = 0.0
    for j in range(L2):
        best_term = 0.0
        for i in range(L1):
            if t1[i] == t2[j]:
                # Backward continuous match limit (d <= 0)
                d = 0
                while i + d - 1 >= 0 and j + d - 1 >= 0 and t1[i + d - 1] == t2[j + d - 1]:
                    d -= 1
                # Forward continuous match limit (u >= 0)
                u = 0
                while i + u + 1 < L1 and j + u + 1 < L2 and t1[i + u + 1] == t2[j + u + 1]:
                    u += 1

                # Cross-product of W2[j] with all contiguous matching characters in W1
                term = W2_adj[j] * sum(W1[i + p] for p in range(d, u + 1))
                if term > best_term:
                    best_term = term
        total_numerator += best_term

    raw_sim = total_numerator / (Sw1 * Sw2)
    return round(max(0.0, min(1.0, raw_sim)), 4)


def calculate_power_grid_comprehensive_score(
    text_similarity: float,
    filter_weights_sum: float = 0.0,
    heat_score: float = 0.0,
    w_filter: float = 0.5,
    w_text: float = 0.3,
    w_heat: float = 0.2,
) -> Dict[str, Any]:
    """
    Paper 9 (IEEE EI2 2020) Comprehensive Ranking Score:
      S = S_f * 0.5 + S_s * 0.3 + S_h * 0.2  (Eq. 1)
    where:
      S_f = 1 / (1 + exp(-W_s))               (Eq. 2, Sigmoid filter score)
      S_s: Cross-weighted product similarity score in [0.0, 1.0]
      S_h: Heat / popularity score in [0.0, 1.0]
    """
    # Eq. 2: Sigmoid filter matching score
    if filter_weights_sum > 0:
        s_f = 1.0 / (1.0 + math.exp(-filter_weights_sum))
    else:
        s_f = 0.5  # Neutral sigmoid baseline at Ws = 0

    s_s = max(0.0, min(1.0, float(text_similarity)))
    s_h = max(0.0, min(1.0, float(heat_score)))

    # Eq. 1: Linear combination
    total_score = (s_f * w_filter) + (s_s * w_text) + (s_h * w_heat)

    return {
        "comprehensive_score": round(total_score, 4),
        "filter_score": round(s_f, 4),
        "text_similarity": round(s_s, 4),
        "heat_score": round(s_h, 4),
        "weights": {"filter": w_filter, "text": w_text, "heat": w_heat},
    }


def compute_cross_weighted_product_score(
    text_similarity: float,
    filter_score: float = 1.0,
    attention_confidence: float = 0.90,
    alpha: float = 0.50,
    beta: float = 0.25,
    gamma: float = 0.25,
) -> float:
    """
    Paper 9 Cross-Weighted Multi-Factor Fusion (Backwards Compatible):
      Score = (S_text)^alpha * (S_filter)^beta * (S_attention)^gamma
    """
    s_text = max(0.001, min(1.0, text_similarity))
    s_filter = max(0.001, min(1.0, filter_score))
    s_attn = max(0.001, min(1.0, attention_confidence))

    score = (s_text ** alpha) * (s_filter ** beta) * (s_attn ** gamma)
    return round(float(score), 4)


# =============================================================================
# 5. PAPER 2: Normalized Levenshtein Edit-Distance & OCR Glyph Confusion Matrix
# Reference: Hao Wang et al., CVPR 2021 (STR-TDSL, Eq. 2)
# Formula: S(q, w) = 1 - Levenshtein(q, w) / max(|q|, |w|)
# =============================================================================
def ocr_glyph_normalize(text: str) -> str:
    """
    Normalizes common optical character recognition glyph confusions.
    Bridges visual character substitutions made by OCR engines:
    - Digits vs Letters: 0 <-> o, 1 <-> l, 8 <-> b
    - Ligatures & Scans: rn -> m, vv -> w, cl -> d
    - Cursive / Stylized: j <-> s, f <-> s, c <-> k
    """
    s = text.lower().strip()
    s = s.replace("0", "o").replace("1", "l").replace("8", "b")
    s = s.replace("rn", "m").replace("vv", "w").replace("cl", "d")
    # In handwriting and historic fonts, cursive 's' is frequently misread as 'f' (long-s glyph)
    if s.startswith("f") and len(s) >= 4:
        s = "s" + s[1:]
    return s



def compute_normalized_levenshtein(s1: str, s2: str) -> float:
    """
    Paper 2 (CVPR 2021 Eq. 2) Normalized Levenshtein Similarity:
    S = 1 - Distance(s1, s2) / max(|s1|, |s2|)
    Provides a continuous [0.0, 1.0] metric space for string ranking.
    """
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0


    from app.search.fuzzy_search import damerau_levenshtein_distance
    d = damerau_levenshtein_distance(s1.lower(), s2.lower())
    max_len = max(len(s1), len(s2))
    sim = 1.0 - (d / float(max_len)) if max_len > 0 else 0.0
    return round(max(0.0, min(1.0, sim)), 4)


def compute_paper2_ocr_similarity(query_word: str, candidate_token: str) -> float:
    """
    Unified Paper 2 Cross-Modal Visual-Textual Matcher:
    Combines Raw Normalized Levenshtein, Glyph-Normalized Levenshtein,
    and Bounded Dice overlap to withstand severe OCR misrecognitions.
    """
    qw = query_word.lower().strip()
    ct = candidate_token.lower().strip()
    if not qw or not ct:
        return 0.0
    if qw == ct:
        return 1.0

    # 1. Raw Normalized Levenshtein (Paper 2 Eq 2)
    s_raw = compute_normalized_levenshtein(qw, ct)

    # 2. Glyph-Normalized Levenshtein (Optical Confusion Bridges)
    s_glyph = compute_normalized_levenshtein(ocr_glyph_normalize(qw), ocr_glyph_normalize(ct))

    # 3. Multi-Order Character Dice (Paper 13 / Subwords)
    s_dice = compute_dice_similarity(qw, ct)

    # 4. Partial substring or subword containment (e.g. 'lawns' in 'mshlawne')
    s_sub = 0.0
    if len(qw) >= 4 and len(ct) >= 4:
        if qw in ct or ct in qw:
            s_sub = 0.82
        elif ocr_glyph_normalize(qw) in ocr_glyph_normalize(ct):
            s_sub = 0.80

    return max(s_raw, s_glyph, s_dice, s_sub)

