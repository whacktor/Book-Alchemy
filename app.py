from flask import Flask, render_template, request, redirect, url_for, flash
import os
from datetime import datetime
from sqlalchemy import or_
from data_models import db, Author, Book

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(basedir, 'data', 'library.sqlite')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SECRET_KEY"] = "dev-secret-key-change-me"

db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/")
def home():
    q = (request.args.get("q") or "").strip()
    sort = request.args.get("sort", "title")       # title | author
    direction = request.args.get("dir", "asc")     # asc | desc

    query = Book.query.join(Author)

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Book.title.ilike(like),
                Book.isbn.ilike(like),
                Author.name.ilike(like),
            )
        )

    if sort == "author":
        order_col = Author.name
    else:
        order_col = Book.title

    order_col = order_col.desc() if direction == "desc" else order_col.asc()
    books = query.order_by(order_col).all()

    message = None
    if q and not books:
        message = f'Keine Bücher gefunden für: "{q}"'

    return render_template(
        "home.html",
        books=books,
        q=q,
        sort=sort,
        direction=direction,
        message=message,
    )


@app.route("/add_author", methods=["GET", "POST"])
def add_author():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        birth_date_str = request.form.get("birth_date", "").strip()
        death_date_str = request.form.get("date_of_death", "").strip()

        if not name:
            flash("Bitte einen Namen eingeben.", "error")
            return render_template("add_author.html")

        birth_date = None
        date_of_death = None

        try:
            if birth_date_str:
                birth_date = datetime.strptime(birth_date_str, "%d.%m.%Y").date()
            if death_date_str:
                date_of_death = datetime.strptime(death_date_str, "%d.%m.%Y").date()
        except ValueError:
            flash("Bitte Datum im Format TT.MM.JJJJ eingeben (z.B. 09.02.2001).", "error")
            return render_template("add_author.html")

        if birth_date and date_of_death and date_of_death < birth_date:
            flash("Das Sterbedatum darf nicht vor dem Geburtsdatum liegen.", "error")
            return render_template("add_author.html")

        author = Author(
            name=name,
            birth_date=birth_date,
            date_of_death=date_of_death
        )

        db.session.add(author)
        db.session.commit()

        flash(f"Autor hinzugefügt: {author.name}", "success")
        return redirect(url_for("add_author"))

    return render_template("add_author.html")


@app.route("/add_book", methods=["GET", "POST"])
def add_book():
    authors = Author.query.order_by(Author.name.asc()).all()

    if request.method == "POST":
        isbn = request.form.get("isbn", "").strip()
        title = request.form.get("title", "").strip()
        publication_year = request.form.get("publication_year", "").strip()
        author_id = request.form.get("author_id", "").strip()

        if not isbn or not title or not author_id:
            flash("Bitte ISBN, Titel und Autor auswählen.", "error")
            return render_template("add_book.html", authors=authors)

        if Book.query.filter_by(isbn=isbn).first():
            flash("Diese ISBN existiert bereits.", "error")
            return render_template("add_book.html", authors=authors)

        try:
            publication_year_value = int(publication_year) if publication_year else None
            author_id_value = int(author_id)
        except ValueError:
            flash("Ungültige Eingabe bei Erscheinungsjahr oder Autor.", "error")
            return render_template("add_book.html", authors=authors)

        book = Book(
            isbn=isbn,
            title=title,
            publication_year=publication_year_value,
            author_id=author_id_value,
        )

        db.session.add(book)
        db.session.commit()
        flash(f"Buch hinzugefügt: {book.title}", "success")
        return redirect(url_for("add_book"))

    return render_template("add_book.html", authors=authors)


@app.route("/book/<int:book_id>/delete", methods=["POST"])
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    author = book.author

    db.session.delete(book)
    db.session.commit()

    if author and Book.query.filter_by(author_id=author.id).count() == 0:
        db.session.delete(author)
        db.session.commit()
        flash(f"Buch gelöscht. Autor '{author.name}' hatte keine weiteren Bücher und wurde ebenfalls entfernt.", "success")
    else:
        flash("Buch erfolgreich gelöscht.", "success")

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
