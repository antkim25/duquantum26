"""Shared helpers: IDs, Pauli strings, result cache, CSV output."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
SUBMISSIONS = ROOT / "submissions"
DATA = ROOT / "data"


def cid(circuit: str, q: int) -> str:
    return f"Duke_{circuit}_{q}"


def z_on(q: int, n: int) -> str:
    """Pauli string with Z on qubit q. q0 is the RIGHTMOST character."""
    return "I" * (n - 1 - q) + "Z" + "I" * q


def cache_path(circuit: str, tag: str) -> Path:
    return RESULTS / circuit / f"{tag}.json"


def load_cache(circuit: str, tag: str) -> dict:
    """{"meta": {...}, "values": {cid: float}, "pending": {cid: job_id}}"""
    p = cache_path(circuit, tag)
    if p.exists():
        return json.loads(p.read_text())
    return {"meta": {}, "values": {}, "pending": {}}


def save_cache(circuit: str, tag: str, cache: dict) -> None:
    p = cache_path(circuit, tag)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, indent=1))
    tmp.replace(p)  # atomic, so a crash never leaves a half-written file


def values_in_order(circuit: str, tag: str, n: int) -> list[float]:
    vals = load_cache(circuit, tag)["values"]
    missing = [q for q in range(n) if cid(circuit, q) not in vals]
    if missing:
        raise ValueError(f"{circuit}/{tag} missing qubits {missing}")
    return [vals[cid(circuit, q)] for q in range(n)]


def write_csv(circuit: str, values: list[float], name: str) -> Path:
    SUBMISSIONS.mkdir(exist_ok=True)
    out = SUBMISSIONS / f"{name}.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["circuit_id", "value"])
        for q, v in enumerate(values):
            w.writerow([cid(circuit, q), repr(float(v))])
    return out
