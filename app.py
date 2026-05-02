import os
from functools import wraps
from datetime import datetime

import requests
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")
NEWS_API_KEY = "e4aa643e87fe4837ab9c32f3417686c8"

# Simple in-memory user store (email -> user data)
USERS = {}

CATEGORY_MAP = {
    "tech": "technology",
    "finance": "business",
    "sports": "sports",
    "health": "health",
    "entertainment": "entertainment",
    "general": "general",
}
DEFAULT_INTEREST = 0.5


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_email" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return wrapper


def get_current_user():
    email = session.get("user_email")
    if not email:
        return None
    return USERS.get(email)


def fetch_news_by_category(category_key):
    mapped_category = CATEGORY_MAP.get(category_key, "general")
    api_key = os.getenv("NEWS_API_KEY", "").strip() or os.getenv("NEWSAPI_KEY", "").strip() or NEWS_API_KEY

    if not api_key:
        return {
            "ok": False,
            "message": "NEWSAPI_KEY is not set. Add it as an environment variable.",
            "articles": [],
            "category": category_key,
        }

    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "apiKey": api_key,
        "category": mapped_category,
        "language": "en",
        "pageSize": 20,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        return {
            "ok": False,
            "message": f"Failed to fetch news: {exc}",
            "articles": [],
            "category": category_key,
        }

    if payload.get("status") != "ok":
        return {
            "ok": False,
            "message": payload.get("message", "NewsAPI returned an error."),
            "articles": [],
            "category": category_key,
        }

    articles = []
    for item in payload.get("articles", []):
        articles.append(
            {
                "title": item.get("title") or "Untitled",
                "description": item.get("description") or "No description available.",
                "source": (item.get("source") or {}).get("name", "Unknown"),
                "url": item.get("url") or "#",
                "image": item.get("urlToImage"),
                "published_at": item.get("publishedAt"),
                "category": category_key.capitalize(),
            }
        )

    return {
        "ok": True,
        "message": "Fetched successfully.",
        "articles": articles,
        "category": category_key,
    }


def normalize_interests(form_data):
    """Parse multi-interest slider values from form data."""
    interests = {}
    for key in CATEGORY_MAP:
        raw_value = form_data.get(f"interest_{key}", str(DEFAULT_INTEREST)).strip()
        try:
            value = float(raw_value)
        except ValueError:
            value = DEFAULT_INTEREST
        # Clamp to supported slider range and step family.
        if value < 0:
            value = 0.0
        if value > 1:
            value = 1.0
        interests[key] = value
    return interests


def active_categories_from_interests(interests):
    return [name for name, score in interests.items() if score > 0]


@app.route("/")
def index():
    if "user_email" in session:
        return redirect(url_for("home"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "user_email" in session:
            return redirect(url_for("home"))
        return render_template("login.html", mode="login")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "").strip()

    user = USERS.get(email)
    if not user or user["password"] != password:
        return render_template(
            "login.html",
            mode="login",
            error="Invalid email or password.",
            email=email,
        )

    session["user_email"] = email
    return redirect(url_for("home"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        if "user_email" in session:
            return redirect(url_for("home"))
        return render_template("login.html", mode="signup")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "").strip()

    if not name or not email or not password:
        return render_template(
            "login.html",
            mode="signup",
            error="All fields are required.",
            name=name,
            email=email,
        )

    if email in USERS:
        return render_template(
            "login.html",
            mode="signup",
            error="User already exists. Please login.",
            name=name,
            email=email,
        )

    USERS[email] = {
        "name": name,
        "password": password,
        "preference": "general",
        "preferences": {key: DEFAULT_INTEREST for key in CATEGORY_MAP},
        "created_at": datetime.utcnow().isoformat(),
    }
    session["user_email"] = email
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/set_preferences", methods=["POST"])
@login_required
def set_preferences():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    # Backward compatible: still supports old single category posts.
    legacy_category = request.form.get("category", "").strip().lower()
    if legacy_category and legacy_category in CATEGORY_MAP:
        user["preference"] = legacy_category
        user["preferences"] = {
            key: (1.0 if key == legacy_category else 0.0) for key in CATEGORY_MAP
        }
        return redirect(url_for("feed"))

    interests = normalize_interests(request.form)
    active_categories = active_categories_from_interests(interests)
    if not active_categories:
        interests["general"] = 1.0
        active_categories = ["general"]

    user["preferences"] = interests
    # Keep legacy field intact for existing logic/compatibility.
    user["preference"] = active_categories[0]
    return redirect(url_for("feed"))


@app.route("/home")
@login_required
def home():
    user = get_current_user()
    return render_template("home.html", user=user)


@app.route("/feed")
@login_required
def feed():
    user = get_current_user()
    selected_category = (user or {}).get("preference", "general")
    preferences = (user or {}).get("preferences")
    if isinstance(preferences, dict):
        active_categories = active_categories_from_interests(preferences)
        if not active_categories:
            active_categories = [selected_category]
    else:
        active_categories = [selected_category]
    return render_template(
        "feed.html",
        user=user,
        category=selected_category,
        active_categories=active_categories,
    )


@app.route("/get_feed")
@login_required
def get_feed():
    user = get_current_user()
    category = request.args.get("category", "").strip().lower()

    if category:
        if category not in CATEGORY_MAP:
            category = "general"
        data = fetch_news_by_category(category)
        return jsonify(data)

    preferences = (user or {}).get("preferences")
    if not isinstance(preferences, dict):
        fallback = (user or {}).get("preference", "general")
        data = fetch_news_by_category(fallback if fallback in CATEGORY_MAP else "general")
        return jsonify(data)

    categories = active_categories_from_interests(preferences)
    if not categories:
        categories = ["general"]

    combined_articles = []
    seen_urls = set()
    errors = []

    for cat in categories:
        result = fetch_news_by_category(cat)
        if not result.get("ok"):
            errors.append(result.get("message", f"Failed for {cat}"))
            continue
        for article in result.get("articles", []):
            url = article.get("url", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)
            combined_articles.append(article)

    if not combined_articles:
        return jsonify(
            {
                "ok": False,
                "message": errors[0] if errors else "No news available for selected interests.",
                "articles": [],
                "category": ", ".join(categories),
            }
        )

    return jsonify(
        {
            "ok": True,
            "message": "Fetched successfully.",
            "articles": combined_articles[:36],
            "category": ", ".join(categories),
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
