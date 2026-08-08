"""Shared helper for turning the sample-size-based confidence signal each
prediction service already computes (number of months/weeks/years of data
available) into a percentage, not just a low/medium/high label (Phase 24).

This doesn't invent new precision — every caller already decides its label
from a count of real records against a threshold (e.g. "high" once there are
12+ months of catch data). pct_from_count() expresses that exact same signal
as a smooth 0-100 number instead of 3 buckets, capped at the same point the
existing "high" threshold kicks in.
"""


def pct_from_count(n: int, full_at: int) -> int:
    """0-100, ramping linearly from 0 to 100 as n goes from 0 to full_at,
    saturating at 100 beyond that. full_at should match wherever the
    caller's own label logic already tops out at "high"/its best tier."""
    if full_at <= 0:
        return 100
    return max(0, min(100, round(100 * n / full_at)))
