from flask import Blueprint, render_template, request, redirect  # pyright: ignore

settings = Blueprint("settings", __name__)


@settings.route("/settings", methods=["GET", "POST"])
def settings_page():
    if request.method == "POST":
        disable_nsfw = request.form.get("disable_nsfw") == "on"
        response = redirect("/settings")
        response.set_cookie(
            "disable_nsfw", "1" if disable_nsfw else "0", max_age=31536000
        )
        return response

    disable_nsfw = request.cookies.get("disable_nsfw", "0") == "1"
    return render_template("settings.html", disable_nsfw=disable_nsfw)
