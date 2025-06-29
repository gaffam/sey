"""Pesticide sensor fusion utilities."""

from typing import Tuple, List, Dict


def fuse_pesticide_signals(extra: Dict[str, float] | None) -> Tuple[float, List[str]]:
    """Return pesticide risk score based on extra sensor readings."""
    if not extra:
        return 0.0, []

    score = 0.0
    reasons: List[str] = []

    voc = extra.get("voc")
    nh3 = extra.get("nh3")
    ph = extra.get("ph")
    orp = extra.get("orp")

    if voc is not None and nh3 is not None:
        if voc > 400 and nh3 > 50:
            score += 0.6
            reasons.append("voc_and_nh3_high")
        elif voc > 400:
            score += 0.3
            reasons.append("voc_high")
    elif voc is not None and voc > 400:
        score += 0.3
        reasons.append("voc_high")

    if orp is not None and orp > 700:
        score += 0.2
        reasons.append("orp_high")

    if ph is not None and (ph < 5.5 or ph > 7.5):
        score += 0.2
        reasons.append("ph_out_of_range")

    # normalize
    if score > 1:
        score = 1.0
    return round(score, 2), reasons
