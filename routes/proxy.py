from flask import Blueprint, Response, request  # pyright: ignore
import requests

proxy = Blueprint("proxy", __name__)


@proxy.route("/img")
def image_proxy():
    image_url = request.args.get("url")
    if not image_url:
        return "No URL provided", 400

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        r = requests.get(image_url, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"Error fetching image: {e}")
        return "Image not found", 404

    content_type = r.headers.get("Content-Type", "image/jpeg")
    return Response(r.content, content_type=content_type)
