"""Demo apps used in treb examples."""
from flask import Flask

app = Flask(__name__)


@app.route("/")
def hello_world():
    """Dummy endpoint."""
    return "<p>Hello, World!</p>"


def main():
    """App launcher."""
    app.run(host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
