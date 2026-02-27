from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from autoprofit.models import DraftPost, Offer

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_post(
    output_dir: Path,
    *,
    post: DraftPost,
    offer: Offer,
    offer_url: str,
    disclosure: str,
    api_base_url: str,
    stripe_enabled: bool,
) -> str:
    posts_dir = output_dir / "posts"
    posts_dir.mkdir(parents=True, exist_ok=True)

    path = posts_dir / f"{post.slug}.html"
    template = _env().get_template("post.html.j2")
    html = template.render(
        post=post,
        offer=offer,
        offer_url=offer_url,
        disclosure=disclosure,
        api_base_url=api_base_url.rstrip("/"),
        stripe_enabled=stripe_enabled,
    )
    path.write_text(html, encoding="utf-8")
    return str(path)


def render_index(output_dir: Path, posts: list[dict[str, str]]) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "index.html"
    template = _env().get_template("index.html.j2")
    html = template.render(posts=posts)
    path.write_text(html, encoding="utf-8")
    return str(path)
