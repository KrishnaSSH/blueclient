from flask import Flask, render_template
from routes.main import main
from routes.wiki import wiki
from routes.settings import settings
from routes.proxy import proxy

app = Flask(__name__)

app.register_blueprint(main)
app.register_blueprint(wiki)
app.register_blueprint(settings)
app.register_blueprint(proxy)


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


if __name__ == "__main__":
    app.run(debug=True)
