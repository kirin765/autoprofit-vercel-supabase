from pathlib import Path

from autoprofit.offers import build_offer_url, choose_offer, load_offers


def test_choose_offer_prefers_category_overlap() -> None:
    offers = load_offers(Path("config/offers.yaml"))
    offer = choose_offer("best ecommerce website store", offers)
    assert offer.slug == "shopify"


def test_offer_url_adds_tracking_params() -> None:
    offers = load_offers(Path("config/offers.yaml"))
    offer = next(item for item in offers if item.slug == "amazon-electronics")
    url = build_offer_url(offer, affiliate_tag="demo-20", keyword="best laptop", slug="best-laptop")
    assert "utm_source=autoprofit" in url
    assert "tag=demo-20" in url
