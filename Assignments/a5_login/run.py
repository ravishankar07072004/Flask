from app import app, init_db

if __name__ == "__main__":
    try:
        init_db()
        print("Database tables are ready.")
    except Exception as exc:
        raise SystemExit(f"Database startup failed: {exc}")
    app.run(debug=app.config.get("DEBUG", True))
