# Monetization And Automation Research Notes

## Sources used for decision making

- FTC endorsement disclosure requirements:
  - https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides
- Amazon Associates participation requirements:
  - https://affiliate-program.amazon.com/help/node/topic/G8TW5AE9XL2VX9VM
- Stripe subscription checkout model:
  - https://docs.stripe.com/payments/checkout/build-subscriptions
- GitHub Actions scheduled automation:
  - https://docs.github.com/en/actions/reference/events-that-trigger-workflows#schedule
- Google AdSense invalid traffic policy:
  - https://support.google.com/adsense/answer/16737
- Google Search spam policy (scaled content abuse):
  - https://developers.google.com/search/docs/essentials/spam-policies

## Decisions applied in this project

1. Always include affiliate disclosure in generated pages by default.
2. Enforce relevance gate: skip publication when no category-offer match exists.
3. Enforce minimum content quality via word-count threshold.
4. Log click/run metrics for optimization and fraud-risk monitoring.
5. Keep scheduled automation in source control (GitHub Actions + local loop mode).
