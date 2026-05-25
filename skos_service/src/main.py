"""
SKOS Codelisten Service für BorderCapControl.
Stellt XAusländer-kompatible Codelisten als REST-Endpunkte bereit.
Daten werden aus lokalen JSON-Dateien gelesen — kein externer HTTP-Call.
"""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="SKOS Codelisten Service",
    version="0.1.0",
    description="XAusländer-Codelisten für BorderCapControl",
)

# Datenpfad relativ zur main.py-Datei
DATA_DIR = Path(__file__).parent / "data"


@app.get("/health")
def health():
    """Health-Check-Endpunkt."""
    return {"status": "ok"}


@app.get("/codes/{list_name}")
def get_codes(list_name: str):
    """
    Gibt eine Codeliste anhand ihres Namens zurück.
    Verfügbare Listen: geschlecht, staatsangehoerigkeit

    Args:
        list_name: Name der Codeliste (entspricht Dateiname ohne .json)

    Returns:
        SKOS-Codeliste als JSON-Objekt

    Raises:
        HTTPException(404): Wenn die Codeliste nicht existiert
    """
    # Nur ASCII-alphanumerische Zeichen und Unterstriche erlaubt (Path-Traversal-Schutz).
    # isascii() + isalnum() verhindert auch Unicode-Lookalikes die isalnum() allein passieren.
    safe_name = "".join(c for c in list_name if c.isascii() and (c.isalnum() or c == "_"))
    if safe_name != list_name:
        raise HTTPException(status_code=400, detail="Ungültiger Codelistenname")

    path = DATA_DIR / f"{safe_name}.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Codeliste '{list_name}' nicht gefunden",
        )

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Codeliste '{safe_name}' ist fehlerhaft (ungültiges JSON): {exc.msg}",
        ) from exc
