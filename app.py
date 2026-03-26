from backend.server import app


if __name__ == "__main__":
    # Production tip: run with `gunicorn -w 2 -b 0.0.0.0:8000 backend.server:app`
    app.run(host="0.0.0.0", port=8000, debug=False)
