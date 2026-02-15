from flask import Blueprint, render_template  # pyright: ignore
from core.fetch import fetch_wiki_page
import markdown

wiki = Blueprint("wiki", __name__)


@wiki.route("/r/<subreddit>/wiki/")
@wiki.route("/r/<subreddit>/wiki/<path:page>")
def wiki_page(subreddit, page="index"):
    wiki_data = fetch_wiki_page(subreddit, page)
    if wiki_data.get("error") == "not_found":
        return render_template("404.html"), 404

    content_html = markdown.markdown(wiki_data.get("content_md", ""))

    return render_template(
        "wiki.html",
        subreddit=subreddit,
        page=page,
        content_html=content_html,
        revision_id=wiki_data.get("revision_id"),
        revision_date=wiki_data.get("revision_date"),
        revision_by=wiki_data.get("revision_by"),
    )
