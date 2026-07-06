import csv
import os
import tempfile
from typing import List, Dict, Optional

from functions import obter_caminho_csv, normalizar_linha_csv

# CSV header used by the app
HEADERS = [
    "Nome da Planta",
    "Tipo",
    "Nome Popular 1",
    "Nome Popular 2",
    "Nome Popular 3",
    "Tempo de Colheita (Em Dias)",
    "Frequência de Rega (Em Dias)",
    "Quantidade de Sol",
    "Planta que Cresce Bem Junto 1",
    "Planta que Cresce Bem Junto 2",
    "Planta que Cresce Bem Junto 3",
    "Planta que Cresce Mal Junto 1",
    "Planta que Cresce Mal Junto 2",
    "Planta que Cresce Mal Junto 3",
    "Fonte 1",
    "Fonte 2",
    "Fonte 3",
]


def get_csv_path() -> str:
    return obter_caminho_csv()


def ensure_csv_exists() -> None:
    path = get_csv_path()
    dirpath = os.path.dirname(path)
    os.makedirs(dirpath, exist_ok=True)
    if not os.path.exists(path) or os.path.getsize(path) < 200:
        try:
            from dados_iniciais import CSV_FABRICA
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(CSV_FABRICA.strip() + "\n")
            return
        except Exception:
            # fallback: write only header
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=HEADERS, delimiter=";")
                writer.writeheader()


def read_all_plants() -> List[Dict[str, str]]:
    path = get_csv_path()
    ensure_csv_exists()
    rows: List[Dict[str, str]] = []
    try:
        with open(path, mode="r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            for r in reader:
                rows.append(normalizar_linha_csv(r))
    except FileNotFoundError:
        pass
    return rows


def write_all_plants(rows: List[Dict[str, str]]) -> None:
    path = get_csv_path()
    dirpath = os.path.dirname(path)
    os.makedirs(dirpath, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix="plantas_", dir=dirpath, text=True)
    os.close(fd)
    try:
        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS, delimiter=";")
            writer.writeheader()
            for r in rows:
                # ensure order and string values
                out = {h: (str(r.get(h, "")) if r.get(h, "") is not None else "") for h in HEADERS}
                writer.writerow(out)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def find_plant_by_name(nome: str) -> Optional[Dict[str, str]]:
    nome_norm = (nome or "").strip().lower()
    for r in read_all_plants():
        if r.get("Nome da Planta", "").strip().lower() == nome_norm:
            return r
    return None


def add_plant(plant: Dict[str, str]) -> bool:
    if not plant.get("Nome da Planta"):
        return False
    nome = plant["Nome da Planta"].strip()
    if find_plant_by_name(nome):
        return False
    rows = read_all_plants()
    # normalize to string values
    rows.append({h: str(plant.get(h, "")) for h in HEADERS})
    write_all_plants(rows)
    return True


def update_plant(nome: str, updates: Dict[str, str]) -> bool:
    nome_norm = (nome or "").strip().lower()
    rows = read_all_plants()
    changed = False
    for r in rows:
        if r.get("Nome da Planta", "").strip().lower() == nome_norm:
            for k, v in updates.items():
                if k in HEADERS:
                    r[k] = str(v)
            changed = True
            break
    if changed:
        write_all_plants(rows)
    return changed


def delete_plant(nome: str) -> bool:
    nome_norm = (nome or "").strip().lower()
    rows = read_all_plants()
    new_rows = [r for r in rows if r.get("Nome da Planta", "").strip().lower() != nome_norm]
    if len(new_rows) == len(rows):
        return False
    write_all_plants(new_rows)
    return True
