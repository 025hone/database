from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date
import matplotlib.pyplot as plt


app = Flask(__name__)
DB_NAME = "notes.db"

# --------------------
# DB 接続
# --------------------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# --------------------
# DB 初期化
# --------------------
def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS lectures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lecture_id INTEGER NOT NULL,
        note_date TEXT,
        content TEXT,
        important INTEGER DEFAULT 0,
        FOREIGN KEY (lecture_id) REFERENCES lectures(id)
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_notes_date ON notes(note_date);")
    conn.commit()
    conn.close()

init_db()

# --------------------
# 一覧・検索（重要メモ優先）
# --------------------
@app.route("/")
def index():
    keyword = request.args.get("keyword", "")
    lecture_id = request.args.get("lecture_id", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    conn = get_db()
    cur = conn.cursor()

    query = """
        SELECT
            notes.id,
            notes.content,
            notes.note_date,
            notes.important,
            lectures.name
        FROM notes
        JOIN lectures ON notes.lecture_id = lectures.id
        WHERE 1=1
    """
    params = []

    if keyword:
        query += " AND notes.content LIKE ?"
        params.append(f"%{keyword}%")

    if lecture_id:
        query += " AND lectures.id = ?"
        params.append(lecture_id)

    if start_date:
        query += " AND notes.note_date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND notes.note_date <= ?"
        params.append(end_date)

    query += """
        ORDER BY
            notes.important DESC,
            notes.note_date DESC
    """

    cur.execute(query, params)
    notes = cur.fetchall()

    lectures = conn.execute("SELECT * FROM lectures").fetchall()
    conn.close()

    return render_template(
        "index.html",
        notes=notes,
        lectures=lectures,
        keyword=keyword,
        lecture_id=lecture_id,
        start_date=start_date,
        end_date=end_date
    )

# --------------------
# ノート追加
# --------------------
@app.route("/add", methods=["POST"])
def add_note():
    lecture_id = request.form["lecture_id"]   # ← 修正ポイント
    content = request.form["content"]
    note_date = request.form["date"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO notes (lecture_id, note_date, content)
        VALUES (?, ?, ?)
    """, (lecture_id, note_date, content))

    conn.commit()
    conn.close()

    return redirect("/")

# --------------------
#講義追加
#---------------------
@app.route("/add_lecture", methods=["GET", "POST"])
def add_lecture():
    if request.method == "POST":
        name = request.form["name"]
        conn = get_db()
        conn.execute("INSERT INTO lectures (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        return redirect(url_for("index"))
    return render_template("add_lecture.html")

# --------------------
# ノート詳細
# --------------------
@app.route("/note/<int:note_id>")
def note_detail(note_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            notes.id,
            notes.content,
            notes.note_date,
            notes.important,
            lectures.name
        FROM notes
        JOIN lectures ON notes.lecture_id = lectures.id
        WHERE notes.id = ?
    """, (note_id,))

    note = cur.fetchone()
    conn.close()

    if note is None:
        return "Not Found", 404

    return render_template("note_detail.html", note=note)

# --------------------
# 編集
# --------------------
@app.route("/note/<int:note_id>/edit", methods=["GET", "POST"])
def edit_note(note_id):
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        content = request.form["content"]
        note_date = request.form["date"]

        cur.execute("""
            UPDATE notes
            SET content = ?, note_date = ?
            WHERE id = ?
        """, (content, note_date, note_id))

        conn.commit()
        conn.close()
        return redirect(url_for("note_detail", note_id=note_id))

    cur.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    note = cur.fetchone()
    conn.close()

    return render_template("edit_note.html", note=note)

# --------------------
# 削除
# --------------------
@app.route("/note/<int:note_id>/delete", methods=["POST"])
def delete_note(note_id):
    conn = get_db()
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

# --------------------
# 重要フラグ切り替え
# --------------------
@app.route("/note/<int:note_id>/important")
def toggle_important(note_id):
    conn = get_db()
    conn.execute("""
        UPDATE notes
        SET important = CASE important WHEN 1 THEN 0 ELSE 1 END
        WHERE id = ?
    """, (note_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


# --------------------
# 起動
# --------------------
if __name__ == "__main__":
    app.run(debug=True)

