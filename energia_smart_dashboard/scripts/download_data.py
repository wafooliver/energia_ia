from pathlib import Path
from urllib.request import urlretrieve

URL = "https://github.com/jlkhermes38/awp-gabarit/raw/main/data/projets/energie.parquet"
DEST = Path(__file__).resolve().parents[1] / "data" / "energie.parquet"
DEST.parent.mkdir(parents=True, exist_ok=True)
print(f"Téléchargement de {URL}")
urlretrieve(URL, DEST)
print(f"Fichier enregistré : {DEST} ({DEST.stat().st_size / 1024 / 1024:.2f} Mo)")
