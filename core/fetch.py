import requests
import time
from typing import Optional, Dict, Any, List


def format_relative_time(timestamp: float) -> str:
    """Convert UTC timestamp to relative time string (e.g. '5h ago')."""
    if not timestamp:
        return ""
    diff = time.time() - timestamp
    if diff < 60:
        return "just now"
    if diff < 3600:
        return f"{int(diff // 60)}m ago"
    if diff < 86400:
        return f"{int(diff // 3600)}h ago"
    if diff < 2592000:
        return f"{int(diff // 86400)}d ago"
    if diff < 31536000:
        return f"{int(diff // 2592000)}mo ago"
    return f"{int(diff // 31536000)}y ago"


BASE_URL = "https://www.reddit.com"
HEADERS = {"User-Agent": "linux:client"}


def _extract_reddit_video_urls(d: Dict[str, Any]) -> Dict[str, Optional[str]]:
    media = d.get("secure_media") or d.get("media") or {}
    if not isinstance(media, dict):
        media = {}

    reddit_video = media.get("reddit_video") or {}
    if not isinstance(reddit_video, dict):
        reddit_video = {}

    mp4 = reddit_video.get("fallback_url")
    hls = reddit_video.get("hls_url")

    # subreddit icon
    sr_detail = d.get("sr_detail") or {}
    subreddit_icon = sr_detail.get("icon_img") or sr_detail.get("community_icon")
    if subreddit_icon and "&amp;" in subreddit_icon:
        subreddit_icon = subreddit_icon.replace("&amp;", "&")

    return {
        "video_mp4": mp4 if isinstance(mp4, str) else None,
        "video_hls": hls if isinstance(hls, str) else None,
        "subreddit_icon": subreddit_icon if isinstance(subreddit_icon, str) else None,
    }


def parse_post(d: Dict[str, Any], brief_len: int = 150) -> Dict[str, Any]:
    """Extract relevant fields from Reddit post JSON."""
    video = _extract_reddit_video_urls(d)
    return {
        "id": d["id"],
        "fullname": d["name"],
        "subreddit": d["subreddit"],
        "subreddit_full": d["subreddit_name_prefixed"],
        "subreddit_id": d.get("subreddit_id"),
        "author": d["author"],
        "author_fullname": d.get("author_fullname"),
        "permalink": f"{BASE_URL}{d['permalink']}",
        "url": d["url"],
        "domain": d["domain"],
        "is_self": d.get("is_self"),
        "title": d.get("title"),
        "selftext": d.get("selftext"),
        "brief": (d.get("selftext") or "")[:brief_len]
        + ("…" if d.get("selftext") else ""),
        "flair": d.get("link_flair_text"),
        "spoiler": d.get("spoiler"),
        "nsfw": d.get("over_18"),
        "score": d.get("score"),
        "upvotes": d.get("ups"),
        "downvotes": d.get("downs"),
        "ratio": d.get("upvote_ratio"),
        "comments_count": d.get("num_comments"),
        "awards": d.get("total_awards_received"),
        "created_utc": d.get("created_utc"),
        "edited": d.get("edited"),
        "locked": d.get("locked"),
        "stickied": d.get("stickied"),
        "archived": d.get("archived"),
        "image": d.get("url_overridden_by_dest")
        if d.get("post_hint") in ["image", "link", "rich:video"]
        or d.get("url", "")
        .lower()
        .split("?")[0]
        .endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".gifv", ".bmp", ".svg"))
        or d.get("domain", "").lower()
        in ["imgur.com", "i.redd.it", "preview.redd.it", "giphy.com", "gfycat.com"]
        else None,
        "thumbnail": d.get("thumbnail"),
        "is_video": d.get("is_video"),
        "media": d.get("secure_media"),
        "preview": d.get("preview"),
        "gallery": d.get("gallery_data"),
        "video_mp4": video["video_mp4"],
        "video_hls": video["video_hls"],
        "subreddit_icon": video["subreddit_icon"],
        "created_rel": format_relative_time(d.get("created_utc")),  # pyright: ignore
    }


def fetch_wiki_page(subreddit: str, page: str = "index") -> Dict[str, Any]:
    """Fetch a wiki page from a subreddit.

    Args:
        subreddit: The subreddit name
        page: The wiki page name (default: "index")

    Returns:
        Dict containing wiki page data
    """
    url = f"{BASE_URL}/r/{subreddit}/wiki/{page}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return {"error": "not_found"}
        raise

    # Check if response is JSON or HTML
    content_type = r.headers.get("Content-Type", "")
    if "application/json" in content_type:
        try:
            data = r.json()["data"]
        except (ValueError, KeyError):
            return {"error": "not_found"}
    else:
        # HTML response - extract content from HTML
        import re

        html = r.text
        # Try to extract wiki content from HTML
        content_match = re.search(
            r'<div[^>]*class="md wiki"[^>]*>(.*?)</div>', html, re.DOTALL
        )
        if content_match:
            content_md = content_match.group(1)
        else:
            content_md = ""

        return {
            "subreddit": subreddit,
            "page": page,
            "content_md": content_md,
            "revision_id": None,
            "revision_date": None,
            "revision_by": None,
        }

    content_md = data.get("content_md", "")

    return {
        "subreddit": subreddit,
        "page": page,
        "content_md": content_md,
        "revision_id": data.get("revision_id"),
        "revision_date": data.get("revision_date"),
        "revision_by": data.get("revision_by", {}).get("data", {}).get("name"),
    }


def fetch_wiki_pages(subreddit: str) -> Dict[str, Any]:
    """Fetch list of wiki pages from a subreddit.

    Args:
        subreddit: The subreddit name

    Returns:
        Dict containing list of wiki pages
    """
    url = f"{BASE_URL}/r/{subreddit}/wiki/pages"
    params = {"raw_json": 1}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return {"error": "not_found"}
        raise

    data = r.json()["data"]
    pages = data.get("data", [])

    return {
        "subreddit": subreddit,
        "pages": pages,
    }


def fetch_posts(
    subreddit: Optional[str] = None,
    username: Optional[str] = None,
    after: Optional[str] = None,
    disable_nsfw: bool = False,
) -> Dict[str, Any]:
    """
    Fetch posts from a subreddit or user.
    Provide either subreddit="funny" or username="reddit"
    """
    if username:
        url = f"{BASE_URL}/user/{username}/submitted.json"
    else:
        subreddit = subreddit or "popular"
        url = f"{BASE_URL}/r/{subreddit}.json"

    params = {"after": after, "sr_detail": 1} if after else {"sr_detail": 1}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return {"posts": [], "after": None, "before": None, "error": "not_found"}
        raise

    data = r.json()["data"]
    posts = [
        parse_post(child["data"], brief_len=500) for child in data.get("children", [])
    ]

    # Filter out NSFW posts if disable_nsfw is True
    if disable_nsfw:
        posts = [p for p in posts if not p.get("nsfw")]

    return {
        "posts": posts,
        "after": data.get("after"),
        "before": data.get("before"),
    }


def fetch_post_by_id(
    post_id: str,
    expand_more_children: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Fetch a single post with its threaded comments.

    By default, this keeps Reddit "more" placeholders in the returned tree.
    Pass expand_more_children to expand only those child IDs (Redlib-style
    incremental loading).
    """

    def _parse_comment(data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "t1",
            "id": data.get("id"),
            "fullname": data.get("name"),
            "parent_fullname": data.get("parent_id"),
            "author": data.get("author"),
            "author_fullname": data.get("author_fullname"),
            "body": data.get("body") or "",
            "score": data.get("score"),
            "created_utc": data.get("created_utc"),
            "created_rel": format_relative_time(data.get("created_utc")),  # pyright: ignore
            "children": [],
        }

    def _collect_from_listing(
        children: List[Dict[str, Any]],
        expand_ids: set[str],
    ) -> tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        by_fullname: Dict[str, Dict[str, Any]] = {}
        more_nodes: List[Dict[str, Any]] = []
        to_expand: List[str] = []

        def walk(items: List[Dict[str, Any]]) -> None:
            for item in items:
                kind = item.get("kind")
                data = item.get("data") or {}
                if kind == "t1":
                    c = _parse_comment(data)
                    if c.get("fullname"):
                        by_fullname[c["fullname"]] = c

                    replies = data.get("replies")
                    if isinstance(replies, dict):
                        walk(replies.get("data", {}).get("children", []) or [])
                elif kind == "more":
                    kids = data.get("children")
                    if isinstance(kids, list):
                        kid_ids = [k for k in kids if isinstance(k, str)]
                        parent_fullname = data.get("parent_id")

                        if expand_ids and all(k in expand_ids for k in kid_ids):
                            to_expand.extend(kid_ids)
                        else:
                            more_nodes.append(
                                {
                                    "type": "more",
                                    "parent_fullname": parent_fullname,
                                    "children": kid_ids,
                                }
                            )

        walk(children)
        return by_fullname, more_nodes, to_expand

    def _fetch_morechildren(
        link_fullname: str, children: List[str]
    ) -> List[Dict[str, Any]]:
        if not children:
            return []

        url = f"{BASE_URL}/api/morechildren.json"
        out: List[Dict[str, Any]] = []

        # Reddit caps children per request (100 is usually safe)
        for i in range(0, len(children), 100):
            chunk = children[i : i + 100]
            payload = {
                "link_id": link_fullname,
                "children": ",".join(chunk),
                "api_type": "json",
                "raw_json": 1,
            }
            try:
                r = requests.post(url, headers=HEADERS, data=payload, timeout=10)
                r.raise_for_status()
            except requests.HTTPError as e:
                if e.response.status_code == 404:
                    continue
                raise
            j = r.json()
            things = j.get("json", {}).get("data", {}).get("things", [])
            if isinstance(things, list):
                out.extend([t for t in things if isinstance(t, dict)])

        return out

    def _build_tree(
        link_fullname: str,
        by_fullname: Dict[str, Dict[str, Any]],
        more_nodes: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        roots: List[Dict[str, Any]] = []
        for c in by_fullname.values():
            parent = c.get("parent_fullname")
            if parent and parent.startswith("t1_") and parent in by_fullname:
                by_fullname[parent]["children"].append(c)
            else:
                # parent is t3_<post> or missing
                roots.append(c)

        for m in more_nodes:
            parent = m.get("parent_fullname")
            if (
                parent
                and isinstance(parent, str)
                and parent.startswith("t1_")
                and parent in by_fullname
            ):
                by_fullname[parent]["children"].append(m)
            else:
                roots.append(m)

        return roots

    url = f"{BASE_URL}/comments/{post_id}.json"
    params = {"limit": 500, "depth": 10, "raw_json": 1, "sr_detail": 1}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return {"error": "not_found"}
        raise

    response = r.json()
    post_data = response[0]["data"]["children"][0]["data"]
    comments_listing = response[1]["data"].get("children", [])

    expand_ids = set(expand_more_children or [])
    by_fullname, more_nodes, to_expand = _collect_from_listing(
        comments_listing, expand_ids
    )
    link_fullname = post_data.get("name") or f"t3_{post_id}"

    if to_expand:
        things = _fetch_morechildren(link_fullname, to_expand)
        new_by_fullname, new_more_nodes, _ = _collect_from_listing(things, set())
        by_fullname.update(new_by_fullname)
        more_nodes.extend(new_more_nodes)

    post = parse_post(post_data)
    post["comments"] = _build_tree(link_fullname, by_fullname, more_nodes)
    return post
