import os
import re
import sqlite3
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from flask import Flask, abort, g, render_template, request, send_from_directory


ROOT = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("PERIODIC_TABLE_DB", ROOT / "data/elementi.db"))
PAGE_SIZE = 50
COMPOUND_KINDS = {"binario", "ternario", "quaternario"}

app = Flask(__name__)
app.config["DATABASE"] = DATABASE


def get_db():
    if "db" not in g:
        if not Path(app.config["DATABASE"]).is_file():
            raise RuntimeError(f"Database SQLite non trovato: {app.config['DATABASE']}")
        g.db = sqlite3.connect(app.config["DATABASE"], timeout=10)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    database = g.pop("db", None)
    if database is not None:
        database.close()


def color_or_default(value, default="#64748B"):
    if value and re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return value
    return default


def get_elements():
    rows = get_db().execute(
        """
        SELECT e.NumAtomico, e.Simbolo, e.Nome, e.NumOx, e.Configurazione,
               t.nome AS tipo, t.colore AS tipo_colore, e.Scoperta,
               e.Elettronegativita, e.MM, e.r, e.VolMolare, e.Densita,
               e.PunFusione, e.PunEbollizione, e.EnIIonizzazione, e.percent,
               e.EntalpiaEvap, e.CalFusione, e.CondElettrica, e.CondTermica,
               e.CalSpecifico, s.nome AS stato, s.colore AS stato_colore,
               e.Gruppo, g.nome AS nome_gruppo, g.colore AS gruppo_colore,
               e.Periodo, p.nome AS nome_periodo, p.colore AS periodo_colore,
               c.nome AS blocco, c.colore AS blocco_colore
        FROM elementi e
        JOIN tipo t ON t.idctrl = e.Tipo
        JOIN stato s ON s.idctrl = e.Stato
        JOIN gruppi g ON g.id = e.Gruppo
        JOIN periodi p ON p.id = e.Periodo
        JOIN ctrl c ON c.idctrl = e.Blocco
        ORDER BY e.NumAtomico
        """
    ).fetchall()
    oxidation_rows = get_db().execute(
        """
        SELECT en.idel, n.nox, n.color
        FROM elenox en
        JOIN numerox n ON n.id = en.idnox
        ORDER BY en.idel, n.nox
        """
    ).fetchall()
    oxidation_by_element = {}
    oxidation_colors = {}
    for row in oxidation_rows:
        oxidation_by_element.setdefault(row["idel"], []).append(str(row["nox"]))
        oxidation_colors.setdefault(
            str(row["nox"]), color_or_default(row["color"])
        )

    elements = []
    for row in rows:
        element = dict(row)
        element["ossidazioni"] = oxidation_by_element.get(element["NumAtomico"], [])
        element["ossidazioni_testo"] = ", ".join(element["ossidazioni"]) or "—"
        element["default_color"] = color_or_default(element["tipo_colore"])
        element["color_type"] = element["default_color"]
        element["color_state"] = color_or_default(element["stato_colore"])
        element["color_block"] = color_or_default(element["blocco_colore"])
        element["color_group"] = color_or_default(element["gruppo_colore"])
        element["color_period"] = color_or_default(element["periodo_colore"])
        element["grid_column"] = (
            element["Gruppo"] - 15 if element["Gruppo"] >= 19 else element["Gruppo"]
        )
        element["grid_row"] = (
            9 if element["Periodo"] == 6 and element["Gruppo"] >= 19
            else 10 if element["Periodo"] == 7 and element["Gruppo"] >= 19
            else element["Periodo"]
        )
        element["color_oxidation"] = oxidation_colors
        elements.append(element)
    return elements


def get_element(atomic_number):
    for element in get_elements():
        if element["NumAtomico"] == atomic_number:
            return element
    return None


def parse_formula(formula, valid_symbols):
    """Return atom counts for a chemical formula, including nested groups and hydrates."""
    formula = formula.strip().translate(str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789"))
    if not formula or len(formula) > 100:
        raise ValueError("Inserisci una formula non vuota (massimo 100 caratteri).")

    total = Counter()
    for segment in re.split(r"[·.]", formula):
        if not segment:
            raise ValueError("La formula contiene un separatore non valido.")
        coefficient_match = re.match(r"^(\d+)(?=[A-Z(\[])", segment)
        coefficient = int(coefficient_match.group(1)) if coefficient_match else 1
        if coefficient < 1:
            raise ValueError("Il coefficiente della formula deve essere positivo.")
        body = segment[coefficient_match.end():] if coefficient_match else segment
        tokens = re.findall(r"[A-Z][a-z]?|\d+|[()\[\]]", body)
        if not tokens or "".join(tokens) != body:
            raise ValueError(f"Formula non valida: «{segment}».")

        index = 0

        def read_count():
            nonlocal index
            if index < len(tokens) and tokens[index].isdigit():
                count = int(tokens[index])
                index += 1
                if count < 1 or count > 100000:
                    raise ValueError("I pedici devono essere compresi tra 1 e 100000.")
                return count
            return 1

        def parse_group(closing=None):
            nonlocal index
            counts = Counter()
            has_content = False
            while index < len(tokens):
                token = tokens[index]
                if token in ")]":
                    if closing is None or token != closing:
                        raise ValueError("Le parentesi della formula non sono bilanciate.")
                    index += 1
                    return counts, has_content
                if token in "([":
                    index += 1
                    nested, nested_has_content = parse_group(")" if token == "(" else "]")
                    if not nested_has_content:
                        raise ValueError("Le parentesi non possono essere vuote.")
                    multiplier = read_count()
                    counts.update({symbol: amount * multiplier for symbol, amount in nested.items()})
                    has_content = True
                    continue
                if token.isdigit():
                    raise ValueError("Un pedice deve seguire un elemento o una parentesi.")
                if token not in valid_symbols:
                    raise ValueError(f"Elemento chimico sconosciuto: {token}.")
                index += 1
                counts[token] += read_count()
                has_content = True
            if closing is not None:
                raise ValueError("Le parentesi della formula non sono bilanciate.")
            return counts, has_content

        segment_counts, has_content = parse_group()
        if not has_content or index != len(tokens):
            raise ValueError(f"Formula non valida: «{segment}».")
        total.update({symbol: amount * coefficient for symbol, amount in segment_counts.items()})

    return total


def safe_wikipedia_name(name):
    if name.casefold() == "calcio":
        name += "_(elemento_chimico)"
    return quote(name.replace(" ", "_"), safe="_()")


@app.get("/assets/<asset_type>/<path:filename>")
def assets(asset_type, filename):
    if asset_type not in {"imgEl", "config"}:
        abort(404)
    return send_from_directory(ROOT / "static" / asset_type, filename)


@app.get("/")
def index():
    elements = get_elements()
    groups = get_db().execute("SELECT id, nome FROM gruppi ORDER BY id").fetchall()
    periods = get_db().execute("SELECT id, nome FROM periodi ORDER BY id").fetchall()
    return render_template(
        "index.html",
        elements=elements,
        groups=groups,
        periods=periods,
        oxidation_values=list(range(-4, 9)),
    )


@app.get("/element/<int:atomic_number>")
def element_detail(atomic_number):
    element = get_element(atomic_number)
    if element is None:
        abort(404)
    fields = [
        ("Configurazione elettronica", element["Configurazione"]),
        ("Massa atomica", element["MM"]),
        ("Tipo", element["tipo"]),
        ("Stato fisico", element["stato"]),
        ("Gruppo", element["nome_gruppo"]),
        ("Periodo", element["nome_periodo"]),
        ("Blocco", element["blocco"]),
        ("Numeri di ossidazione", element["ossidazioni_testo"]),
        ("Scoperta", element["Scoperta"]),
        ("Elettronegatività", element["Elettronegativita"]),
        ("Raggio atomico", element["r"]),
        ("Volume molare", element["VolMolare"]),
        ("Densità", element["Densita"]),
        ("Punto di fusione", element["PunFusione"]),
        ("Punto di ebollizione", element["PunEbollizione"]),
        ("Energia di ionizzazione", element["EnIIonizzazione"]),
        ("Abbondanza", element["percent"]),
        ("Entalpia di evaporazione", element["EntalpiaEvap"]),
        ("Calore di fusione", element["CalFusione"]),
        ("Conducibilità elettrica", element["CondElettrica"]),
        ("Conducibilità termica", element["CondTermica"]),
        ("Calore specifico", element["CalSpecifico"]),
    ]
    return render_template(
        "element.html",
        element=element,
        fields=fields,
        wikipedia_name=safe_wikipedia_name(element["Nome"]),
    )


@app.route("/calculator", methods=["GET", "POST"])
def calculator():
    formula = ""
    error = None
    result = None
    if request.method == "POST":
        formula = request.form.get("formula", "").strip()
        try:
            symbols = {
                row["Simbolo"]
                for row in get_db().execute("SELECT Simbolo FROM elementi")
            }
            atom_counts = parse_formula(formula, symbols)
            placeholders = ",".join("?" for _ in atom_counts)
            masses = {
                row["Simbolo"]: row
                for row in get_db().execute(
                    f"SELECT Simbolo, Nome, MM FROM elementi WHERE Simbolo IN ({placeholders})",
                    tuple(atom_counts),
                )
            }
            breakdown = []
            total_mass = 0.0
            for symbol, count in sorted(atom_counts.items()):
                element = masses[symbol]
                partial_mass = element["MM"] * count
                total_mass += partial_mass
                breakdown.append(
                    {
                        "symbol": symbol,
                        "name": element["Nome"],
                        "count": count,
                        "atomic_mass": element["MM"],
                        "partial_mass": partial_mass,
                    }
                )
            result = {"breakdown": breakdown, "total_mass": total_mass}
        except ValueError as exc:
            error = str(exc)
    return render_template("calculator.html", formula=formula, error=error, result=result)


@app.get("/compounds")
def compounds():
    database = get_db()
    kinds = database.execute(
        "SELECT DISTINCT com FROM elebin ORDER BY com"
    ).fetchall()
    kind_options = sorted(
        (row["com"] for row in kinds if row["com"] in COMPOUND_KINDS),
        key=lambda value: ("binario", "ternario", "quaternario").index(value),
    )
    selected_kind = request.args.get("kind", "binario")
    if selected_kind not in COMPOUND_KINDS:
        selected_kind = "binario"

    symbols = [
        row["Simbolo"]
        for row in database.execute(
            """
            SELECT DISTINCT e.Simbolo
            FROM binari b
            JOIN elebin eb ON eb.idcom = b.ID
            JOIN elementi e ON e.NumAtomico = eb.idel
            WHERE eb.com = ?
            ORDER BY e.Simbolo
            """,
            (selected_kind,),
        )
    ]
    selected_symbol = request.args.get("element", "")
    if selected_symbol not in symbols:
        selected_symbol = symbols[0] if symbols else ""

    categories = database.execute(
        "SELECT ID, nome FROM tipologia WHERE nome <> 'tutti' ORDER BY nome"
    ).fetchall()
    category_ids = {str(row["ID"]) for row in categories}
    selected_category = request.args.get("category", "")
    if selected_category not in category_ids:
        selected_category = ""
    search = request.args.get("q", "").strip()[:100]
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1

    conditions = ["eb.com = ?", "e.Simbolo = ?"]
    params = [selected_kind, selected_symbol]
    if selected_category:
        conditions.append("b.idTipologia = ?")
        params.append(selected_category)
    if search:
        conditions.append(
            "(b.formula LIKE ? OR b.nomeTradizionale LIKE ? OR b.nomeIUPAC LIKE ?)"
        )
        term = f"%{search}%"
        params.extend([term, term, term])
    where_clause = " AND ".join(conditions)

    total = database.execute(
        f"""
        SELECT COUNT(DISTINCT b.ID)
        FROM binari b
        JOIN elebin eb ON eb.idcom = b.ID
        JOIN elementi e ON e.NumAtomico = eb.idel
        WHERE {where_clause}
        """,
        params,
    ).fetchone()[0]
    page_count = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, page_count)
    offset = (page - 1) * PAGE_SIZE
    results = database.execute(
        f"""
        SELECT DISTINCT b.ID, b.formula, b.nomeTradizionale, b.nomeIUPAC,
               b.REAZIONE, t.nome AS tipologia, b.MM
        FROM binari b
        JOIN elebin eb ON eb.idcom = b.ID
        JOIN elementi e ON e.NumAtomico = eb.idel
        JOIN tipologia t ON t.ID = b.idTipologia
        WHERE {where_clause}
        ORDER BY b.formula COLLATE NOCASE
        LIMIT ? OFFSET ?
        """,
        (*params, PAGE_SIZE, offset),
    ).fetchall()
    return render_template(
        "compounds.html",
        kinds=kind_options,
        selected_kind=selected_kind,
        symbols=symbols,
        selected_symbol=selected_symbol,
        categories=categories,
        selected_category=selected_category,
        search=search,
        results=results,
        total=total,
        page=page,
        page_count=page_count,
    )


@app.get("/about")
def about():
    return render_template("about.html")


if __name__ == "__main__":
    app.run(
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_PORT", "5000")),
        debug=False,
    )
