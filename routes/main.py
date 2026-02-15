from flask import Blueprint, render_template, request, redirect  # pyright: ignore
from core.fetch import fetch_posts, fetch_post_by_id
from core.render import (
    enrich_listing_with_rendered_fields,
    enrich_post_with_rendered_fields,
)
import requests

main = Blueprint("main", __name__)


@main.route("/")
def home():
    after = request.args.get("after")
    disable_nsfw = request.cookies.get("disable_nsfw", "0") == "1"
    data = fetch_posts(after=after, disable_nsfw=disable_nsfw)
    enrich_listing_with_rendered_fields(data)
    return render_template("index.html", subreddit="popular", **data)


@main.route("/r/<subreddit>")
def subreddit_page(subreddit):
    after = request.args.get("after")
    disable_nsfw = request.cookies.get("disable_nsfw", "0") == "1"
    data = fetch_posts(subreddit=subreddit, after=after, disable_nsfw=disable_nsfw)
    enrich_listing_with_rendered_fields(data)
    return render_template("index.html", subreddit=subreddit, **data)


@main.route("/r/<subreddit>/")
def subreddit_page_slash(subreddit: str):
    return redirect(f"/r/{subreddit}", code=301)


@main.route("/u/<username>")
def user_page(username):
    after = request.args.get("after")
    disable_nsfw = request.cookies.get("disable_nsfw", "0") == "1"
    data = fetch_posts(username=username, after=after, disable_nsfw=disable_nsfw)
    if data.get("error") == "not_found":
        return render_template("404.html"), 404
    enrich_listing_with_rendered_fields(data)
    return render_template(
        "index.html",
        subreddit=f"u/{username}",
        username=username,
        **data,
    )


@main.route("/u/<username>/")
def user_page_slash(username: str):
    return redirect(f"/u/{username}", code=301)


@main.route("/r/<subreddit>/comments/<post_id>/")
@main.route("/r/<subreddit>/comments/<post_id>")
@main.route("/r/<subreddit>/comments/<post_id>/<slug>/")
@main.route("/r/<subreddit>/comments/<post_id>/<slug>")
def post_page(subreddit: str, post_id: str, slug: str = ""):
    more = request.args.get("more")
    expand_more_children = [x for x in (more.split(",") if more else []) if x]
    focus = request.args.get("focus")
    try:
        post = fetch_post_by_id(post_id, expand_more_children=expand_more_children)
    except requests.HTTPError:
        return "Post not found", 404

    enrich_post_with_rendered_fields(post)

    if focus and isinstance(post.get("comments"), list):

        def find_comment(items, fullname: str):
            for c in items:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "t1" and c.get("fullname") == fullname:
                    return c
                children = c.get("children")
                if isinstance(children, list):
                    found = find_comment(children, fullname)
                    if found:
                        return found
            return None

        focused = find_comment(post["comments"], focus)
        if focused:
            post["comments"] = [focused]
    return render_template("post.html", post=post, subreddit=subreddit)


@main.route("/comments/<post_id>/")
@main.route("/comments/<post_id>")
@main.route("/comments/<post_id>/<slug>/")
@main.route("/comments/<post_id>/<slug>")
def post_page_short(post_id: str, slug: str = ""):
    try:
        post = fetch_post_by_id(post_id)
    except requests.HTTPError:
        return "Post not found", 404

    subreddit = post.get("subreddit") or "popular"
    if slug:
        return redirect(f"/r/{subreddit}/comments/{post_id}/{slug}/", code=301)
    return redirect(f"/r/{subreddit}/comments/{post_id}/", code=301)


@main.route("/post/<post_id>")
def legacy_post_page(post_id: str):
    subreddit = request.args.get("subreddit")
    if subreddit:
        return redirect(f"/r/{subreddit}/comments/{post_id}/", code=301)
    return redirect(f"/r/popular/comments/{post_id}/", code=301)
