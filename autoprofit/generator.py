from __future__ import annotations

from autoprofit.models import DraftPost, Offer, TrendItem


def generate_post(trend: TrendItem, offer: Offer) -> DraftPost:
    keyword = trend.keyword.strip()
    title = f"{keyword}: Buying Guide + Best Option Right Now"

    summary = (
        f"{keyword} is attracting search demand. This page translates the trend into "
        "a practical buying decision with a direct offer, clear tradeoffs, and an execution plan "
        "you can apply immediately without a long setup cycle."
    )

    sections = [
        (
            "Why this trend matters",
            (
                f"Interest around '{keyword}' is rising. High search velocity usually means people "
                "are actively comparing products and prices. Acting during this window captures "
                "high-intent clicks that convert better than generic traffic. Instead of publishing "
                "broad educational content, focus this page on decision-stage intent: clear use case, "
                "budget guidance, and one strong recommended action. That structure improves both user "
                "satisfaction and monetization consistency because visitors do not need to navigate "
                "multiple pages to complete their evaluation."
            ),
        ),
        (
            "What to evaluate before buying",
            (
                "Prioritize total cost of ownership, refund policy, social proof, and onboarding speed. "
                "Ignoring one of these usually increases churn and refund risk. In practice, compare "
                "30-day outcomes rather than feature lists: how fast can a new user get value, what "
                "integration friction appears, and what hidden fees show up after the trial period. "
                "This decision framework protects conversion quality and filters out offers that look "
                "cheap up front but create support overhead later."
            ),
        ),
        (
            f"Recommended pick: {offer.name}",
            (
                f"{offer.name} aligns with this trend category and has a competitive commission profile. "
                "The call-to-action below routes through tracked attribution so performance can be measured "
                "and optimized. Keep the CTA specific and outcome-oriented: visitors should know exactly "
                "what they get after the click. When a campaign underperforms, rotate the headline angle "
                "first, then test an alternative offer in the same category to preserve topical relevance "
                "while improving earnings per click."
            ),
        ),
        (
            "Automation and optimization loop",
            (
                "Every run logs generated content and affiliate click events in SQLite. "
                "Use this data to rank offers by earnings-per-click and gradually remove low-performing campaigns. "
                "A strong operating rhythm is: publish, collect at least one week of click data, compare conversion "
                "signals by keyword family, and then either double down or sunset. This turns the project into a "
                "repeatable revenue system instead of a one-off content experiment and reduces the need for daily "
                "manual intervention."
            ),
        ),
    ]

    return DraftPost(
        slug="",
        title=title,
        keyword=keyword,
        summary=summary,
        sections=sections,
    )
