from __future__ import annotations

import re
from typing import Any, Dict

import bleach  # pyright: ignore
import markdown


_ALLOWED_TAGS = [
    "a",
    "blockquote",
    "br",
    "code",
    "em",
    "hr",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "ul",
]

_ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "title", "loading"],
}


_REDDIT_REF_RE = re.compile(r"(?<![\w/])(?P<prefix>[ru])/(?P<name>[A-Za-z0-9_]+)")

_REDDIT_IMAGE_URL_RE = re.compile(
    r"https?://(?:preview\.redd\.it|i\.redd\.it)/\S+?\.(?:png|jpg|jpeg|gif|webp)(?:\?\S+)?",
    re.IGNORECASE,
)


def _rewrite_local_refs(text: str) -> str:
    if not text:
        return ""

    def repl(m: re.Match[str]) -> str:
        prefix = m.group("prefix")
        name = m.group("name")
        label = f"{prefix}/{name}"
        href = f"/{prefix}/{name}"
        return f"[{label}]({href})"

    return _REDDIT_REF_RE.sub(repl, text)


def _embed_reddit_image_links(text: str) -> str:
    if not text:
        return ""

    def repl(m: re.Match[str]) -> str:
        url = m.group(0)
        i = m.start()

        # Skip URLs that are already part of markdown/image syntax.
        if i >= 2 and text[i - 2 : i] == "](":
            return url
        if i >= 1 and text[i - 1 : i] == "(":
            return url
        if i >= 1 and text[i - 1 : i] == '"':
            return url
        return f"![]({url})"

    return _REDDIT_IMAGE_URL_RE.sub(repl, text)


def render_markdown(text: str) -> str:
    if not text:
        return ""

    text = _embed_reddit_image_links(text)
    text = _rewrite_local_refs(text)

    html = markdown.markdown(
        text,
        extensions=["extra", "nl2br", "sane_lists"],
        output_format="html",
    )

    cleaned = bleach.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        strip=True,
    )

    return bleach.linkify(cleaned)


def enrich_post_with_rendered_fields(post: Dict[str, Any]) -> Dict[str, Any]:
    brief = post.get("brief") or ""
    selftext = post.get("selftext") or ""

    post["brief_html"] = render_markdown(brief)
    post["selftext_html"] = render_markdown(selftext)

    comments = post.get("comments")
    if isinstance(comments, list):

        def walk(items: list[Dict[str, Any]]) -> None:
            for c in items:
                if c.get("type") == "t1":
                    c["body_html"] = render_markdown(c.get("body") or "")
                children = c.get("children")
                if isinstance(children, list):
                    walk([x for x in children if isinstance(x, dict)])

        walk([x for x in comments if isinstance(x, dict)])

    return post


def enrich_listing_with_rendered_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    posts = data.get("posts")
    if isinstance(posts, list):
        for p in posts:
            if isinstance(p, dict):
                enrich_post_with_rendered_fields(p)
    return data

