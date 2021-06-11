import os
import requests

from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Check if table users exists and create it if not:
if not engine.dialect.has_table(engine, "users"):
    db.execute("CREATE TABLE users (id SERIAL PRIMARY KEY, \
                                    username VARCHAR NOT NULL, \
                                    password VARCHAR NOT NULL)")
    print(f"Created table books.")
    db.commit()
    db.close()

# Check if table reviews exists and create it if not:
if not engine.dialect.has_table(engine, "reviews"):
    db.execute("CREATE TABLE reviews (  id SERIAL PRIMARY KEY, \
                                        user_id INTEGER REFERENCES users, \
                                        username VARCHAR, \
                                        book_id INTEGER REFERENCES books, \
                                        rating INTEGER NOT NULL, \
                                        review VARCHAR)")
    print(f"Created table reviews.")
    db.commit()
    db.close()

# Home page
@app.route("/home", methods=["GET"])
def home():
    if session.get("login") is None:
        session["login"] = False
    if session.get("login") is False:
        return render_template("login.html")
    if session.get("login") is True:
        return render_template("home.html", username=session.get("username"))

# Login page
@app.route("/login", methods=["GET"])
def login():
    if session.get("login") is None:
        session["login"] = False
    if session.get("login") is False:
        return render_template("login.html")
    if session.get("login") is True:
        return render_template("home.html")

# Logout method
@app.route("/logout", methods=["GET"])
def logout():
    session["login"] = False
    return redirect ("/login", 302)

# Login check
@app.route("/loginCheck", methods=["POST"])
def loginCheck():
    username = request.form.get("username").lower()
    password = request.form.get("password")
    try:
        userCheck = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchone()[1]
        db.commit()
        db.close()
        passCheck = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchone()[2]
        db.commit()
        db.close()
    except:
        db.rollback()
        return render_template("loginFailed.html")
    if  username == userCheck and password == passCheck:
        session["login"] = True
        session["username"] = username
        return redirect ("/home", 302)
    return render_template("loginFailed.html")

# Index page
@app.route("/", methods=["GET"])
def index():
    if session.get("login") is None:
        session["login"] = False
    if session.get("login") is False:
        return redirect ("/login", 302)
    if session.get("login") is True:
        return redirect ("/home", 302)

# Register page
@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")

# Add user
@app.route("/addUser", methods=["POST"])
def addUser():
    username = request.form.get("username").lower()
    password = request.form.get("password")
    if username != '' and password != '':
        try:
            db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {"username": username, "password": password})
            db.commit()
            db.close()
            return render_template("registerSuccessful.html")
        except:
            db.rollback()
            return render_template("error.html", message="There was a weird error...")
    return render_template("registerFailed.html")

# Test route
@app.route("/test", methods=["GET", "POST"])
def test():
    return render_template("test.html")

# Search book
@app.route("/searchBook", methods=["POST"])
def searchBook():
    book = request.form.get("book")
    try:
        books = db.execute(f"SELECT * FROM books WHERE lower(title) LIKE lower('%{book}%') OR isbn LIKE '%{book}%' OR lower(author) LIKE lower('%{book}%')").fetchall()
        db.commit()
        db.close()
        if len(books) == 0:
            return render_template("noResults.html", book=book)
    except:
        db.rollback()
        return render_template("noResults.html", book=book)
    return render_template("foundBooks.html", books=books)

# Book page
@app.route("/books/<int:book_id>", methods=["GET"])
def book(book_id):
    # Retrieve book info
    try:
        book = db.execute("SELECT * FROM books WHERE id = :id", {"id": book_id}).fetchone()
        db.commit()
        db.close()
        if book is None:
            return render_template("error.html", message="Book id not found.")
    except:
        db.rollback()
        return render_template("error.html", message="There was a weird error...")

    # Retrieve reviews for that book
    try:
        reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {"book_id": book.id}).fetchall()
        db.commit()
        db.close()
    except:
        db.rollback()
        return render_template("error.html", message="There was a weird error...")

    cookies_dict = {"ccsid":"120-7293333-2622602", "locale":"en", "p":"k9NCq0Z7yQv8WPcN4Gag0SCXtXm-f0yYVNWGglURXNOXgztL", "fbl":"true", "likely_has_account":"true", "blocking_sign_in_interstitial":"true", "u":"PqWH9SWPj-9MvSwlhddx7RrpkRXok3ORsK_4ocmMqxRP90jy", "_session_id2":"728b62c6a3b022ca20502b2809605c3c"}

    # Get Goodreads API info for this book
    res = requests.get("https://www.goodreads.com/book/review_counts.json", cookies=cookies_dict, params={"key": "kAz5BOFBZgT6hcu6H0rMGQ", "isbns": book.isbn})

    print(book.isbn)
    print(res.url)

    # Render book template
    return render_template("book.html", book=book, reviews=reviews, res=res)

# Add review
@app.route("/addReview", methods=["POST"])
def addReview():
    # Retrieve session info
    username = session.get("username")

    # Retrieve form info
    book_id = request.form.get("book_id")
    rating = request.form.get("rating")
    review = request.form.get("review")

    # Retrieve database data
    try:
        user_id = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchone().id
        reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id AND user_id = :user_id", {"book_id": book_id, "user_id": user_id}).fetchall()
        db.commit()
        db.close()
    except:
        db.rollback()
        return render_template("error.html", message="There was a weird error...")

    if rating != '' and review != '' and reviews == []:
        db.execute("INSERT INTO reviews (user_id, username, book_id, rating, review) VALUES (:user_id, :username, :book_id, :rating, :review)",
                    {"user_id": user_id, "username": username, "book_id": book_id, "rating": rating, "review": review})
        db.commit()
        db.close()
        return redirect (url_for('book', book_id=book_id), 302)
    if rating == '' or review == '':
        return render_template("error.html", message="Please make sure that the review field is not empty!")
    if reviews != []:
        return render_template("error.html", message="You already made a review for this book! More than one review per user for a book is not allowed.")
    return redirect (url_for('book', book_id=book_id), 302)

# Renegade's page API
@app.route("/api/<isbn>")
def renegade_api(isbn):
    """Return details about a book."""

    # Make sure book exists.
    try:
        book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
        db.commit()
        db.close()
        if book is None:
            return jsonify({"error": "ISBN not found"}), 404
    except:
        db.rollback()
        return render_template("error.html", message="There was a weird error processing book...")

    # Retrieve reviews for that book
    try:
        reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {"book_id": book.id}).fetchall()
        db.commit()
        db.close()
    except:
        db.rollback()
        return render_template("error.html", message="There was a weird error processing reviews...")

    # Calculate review count and average score
    reviewNum = 0
    averageRat = 0
    for review in reviews:
        reviewNum += 1
        averageRat += review.rating
    if reviewNum != 0:
        averageRat = averageRat/reviewNum
    else:
        averageRat = "n/a"

    # Return json file
    return jsonify({
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "isbn": book.isbn,
        "review_count": reviewNum,
        "average_score": averageRat
      })
