# Tape4el — versione web

Applicazione Flask autonoma pronta per un server Python. La cartella contiene l'applicazione, i template, gli stili, le immagini necessarie e una copia del database SQLite: non dipende dai file Java o dalle cartelle sorgenti del progetto.

## Requisiti

- Python 3.9 o successivo
- Accesso al server per installare i pacchetti Python

## Installazione e avvio in produzione

Copia la cartella `tape4el` sul server e, dalla cartella:

```bash
cd tape4el
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
gunicorn --workers 2 --bind 127.0.0.1:8000 wsgi:application
```

Il processo Gunicorn resta in ascolto su `127.0.0.1:8000`. Per renderlo raggiungibile dal dominio, configura il reverse proxy del server (ad esempio Nginx o Apache) verso quell'indirizzo e abilita HTTPS. Per un server gestito da un pannello di controllo, configura l'applicazione WSGI usando `wsgi.py` e l'oggetto `application`.

Non usare il server di sviluppo Flask (`python app.py`) come servizio pubblico di produzione.

## Verifica in locale

```bash
cd tape4el
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Apri <http://127.0.0.1:5000>.

## Test

Dalla cartella `tape4el`:

```bash
python -m unittest discover -s tests -v
```

## Database

Il database incluso è `data/elementi.db`. Per usare una copia esterna, configura la variabile d'ambiente `PERIODIC_TABLE_DB` con il percorso assoluto del file SQLite. Il processo del server deve poter leggere il file e la sua directory.

## Funzioni

- Tavola periodica responsive, ricerca per nome/simbolo e filtri per tipo, gruppo, periodo, blocco, stato fisico e numero di ossidazione.
- Schede degli elementi con proprietà, configurazione elettronica e collegamento a Wikipedia.
- Calcolo della massa molare, incluse parentesi annidate e formule di sali idrati.
- Ricerca dei composti binari, ternari e quaternari, con filtro per elemento/tipologia e paginazione.
