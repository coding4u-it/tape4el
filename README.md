# TavPerEle Web

Versione web in Python e Flask della tavola periodica desktop. L'app riutilizza il database SQLite e le immagini già presenti in `src/`.

## Avvio in locale

Richiede Python 3.9 o successivo.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Apri <http://127.0.0.1:5000>.

Per indicare un database SQLite in un'altra posizione:

```bash
PERIODIC_TABLE_DB=/percorso/elementi.db python app.py
```

## Funzioni

- Tavola periodica responsive, ricerca per nome/simbolo e colorazione per tipo, gruppo, periodo, blocco, stato fisico o numero di ossidazione.
- Scheda di ciascun elemento, con proprietà, immagine della configurazione elettronica e collegamento a Wikipedia.
- Calcolo della massa molare da formule con parentesi annidate e sali idrati.
- Ricerca dei composti binari, ternari e quaternari, con filtro per elemento e tipologia e paginazione.

## Test

```bash
python -m unittest discover -s tests
```

Per un server WSGI, esponi l'oggetto `app` dal modulo `app.py` e configura `PERIODIC_TABLE_DB` se il database non si trova nel percorso predefinito.
