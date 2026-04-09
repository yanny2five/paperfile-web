import sys
import os

sys.path.append(os.path.dirname(__file__))

print("1. starting imports")

from flask import Flask, request
from modules.searchdata import SearchData
from modules.readdata import CNTReader

print("2. imports finished")

app = Flask(__name__)

print("3. about to load CNTReader")
reader = CNTReader()
print("4. CNTReader loaded")

data = reader.get_data()
print("5. data length =", len(data))

searcher = SearchData(data)
print("6. SearchData ready")

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        author = request.form.get("author", "").strip()
        title = request.form.get("title", "").strip()

        results = searcher.fuzzy_search_by_author_title(
            author_text=author,
            title_text=title
        )

        html = "<h1>Results</h1>"
        html += '<a href="/">Back</a><br><br>'

        if results:
            for paper in results:
                html += f"<b>{paper.get('title', 'No title')}</b><br>"
                html += f"{paper.get('authors', 'No authors')}<br><br>"
        else:
            html += "No results found."

        return html

    return """
    <h1>Paper Search</h1>
    <form method="POST">
        Author: <input name="author"><br><br>
        Title: <input name="title"><br><br>
        <button type="submit">Search</button>
    </form>
    """

if __name__ == "__main__":
    print("7. starting flask")
    app.run(host="127.0.0.1", port=5000, debug=True)