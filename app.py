from flask import Flask, render_template, request
from modules.readdata import CNTReader
from modules.search_service import search_papers, sort_results
from modules.formatters import format_paper

app = Flask(__name__)

reader = CNTReader()
PAPERS = reader.get_data()

print("PAPERS LOADED:", len(PAPERS))
if PAPERS:
    print("FIRST PAPER:", PAPERS[0])


@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    formatted_results = []

    if request.method == "POST":
        search_type = request.form.get("search_type", "author_title")
        sort_by = request.form.get("sort_by", "title")
        year_min = request.form.get("year_min") or None
        year_max = request.form.get("year_max") or None

        if request.form.get("restrict_vita_types"):
            vita_types = request.form.getlist("vita_types")
        else:
            vita_types = []

        italics = "italics" in request.form
        omit_number = "omit_number" in request.form
        omit_keywords = "omit_keywords" in request.form

        # Map search type to the correct form field name
        if search_type == "author_title":
            author_query = request.form.get("author_query", "")
            title_query = request.form.get("title_query", "")
            query = {
                "author": author_query,
                "title": title_query,
            }
        else:
            # Get query from the appropriate field based on search_type
            query_field_map = {
                "number": "query_number",
                "multiple_numbers": "query_multiple_numbers",
                "keyword": "query_keyword",
                "journal_book": "query_journal_book",
                "year": "query_year",
                "vita_type": "query_vita_type",
                "any_field": "query_author_title",
            }
            field_name = query_field_map.get(search_type, "query_author_title")
            query = request.form.get(field_name, "")

        results = search_papers(
            PAPERS,
            query=query,
            search_type=search_type,
            year_min=year_min,
            year_max=year_max,
            vita_types=vita_types,
        )

        results = sort_results(results, sort_by)

        formatted_results = [
            format_paper(
                paper,
                italics=italics,
                omit_number=omit_number,
                omit_keywords=omit_keywords,
            )
            for paper in results
        ]

        print("=" * 80)
        print("SEARCH EXECUTION LOG")
        print("=" * 80)
        print(f"Search Type:       {search_type}")
        print(f"Query:             {query}")
        print(f"Year Range:        {year_min} to {year_max}")
        print(f"Vita Types Filter: {vita_types if vita_types else 'None'}")
        print(f"Sort By:           {sort_by}")
        print(f"Results Found:     {len(results)}")
        print("=" * 80)

    return render_template(
        "index.html",
        results=results,
        formatted_results=formatted_results,
        search_type=request.form.get("search_type", "author_title"),
        query_number=request.form.get("query_number", ""),
        query_multiple_numbers=request.form.get("query_multiple_numbers", ""),
        query_keyword=request.form.get("query_keyword", ""),
        query_journal_book=request.form.get("query_journal_book", ""),
        query_year=request.form.get("query_year", ""),
        query_vita_type=request.form.get("query_vita_type", ""),
        query_author_title=request.form.get("query_author_title", ""),
        author_query=request.form.get("author_query", ""),
        title_query=request.form.get("title_query", ""),
        sort_by=request.form.get("sort_by", "title"),
        year_min=request.form.get("year_min", ""),
        year_max=request.form.get("year_max", ""),
    )


if __name__ == "__main__":
    app.run(debug=True)