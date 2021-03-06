import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():

    db.execute("CREATE TABLE books (id SERIAL PRIMARY KEY, isbn VARCHAR NOT NULL, title VARCHAR NOT NULL, \
    author VARCHAR NOT NULL, year INTEGER NOT NULL)")
    print(f"Created table books.")
    db.commit()

    i = 0
    f = open("books.csv")
    reader = csv.reader(f)
    for isbn, title, author, year in reader:
        if i != 0:
            db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                        {"isbn": isbn, "title": title, "author": author, "year": int(year)})
            print(f"Added book with isbn {isbn}.")
        i += 1
    db.commit()

if __name__ == "__main__":
    main()