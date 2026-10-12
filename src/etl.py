"""ETL: raw (JSON lines) -> curated (Parquet particionado por fecha).

Reglas de calidad:
  1. event_id y user_id no nulos
  2. event_name dentro del catalogo permitido
  3. event_ts parseable
  4. sin duplicados por event_id
Lo rechazado se guarda en data/rejected para auditoria (no se descarta en silencio).
"""
from pathlib import Path

import pandas as pd

VALID_EVENTS = {"signup", "onboarding_complete", "feature_used",
                "add_to_cart", "purchase", "session_start"}


def run(raw="data/raw/events.jsonl", curated="data/curated/events",
        rejected="data/rejected/events.parquet") -> dict:
    df = pd.read_json(raw, lines=True, dtype=False)
    total = len(df)
    df["event_ts"] = pd.to_datetime(df["event_ts"], errors="coerce", utc=True)

    invalid = (df["event_id"].isna() | df["user_id"].isna()
               | ~df["event_name"].isin(VALID_EVENTS) | df["event_ts"].isna())
    rej, ok = df[invalid], df[~invalid]

    n_before = len(ok)
    ok = ok.drop_duplicates(subset="event_id", keep="first")
    n_dups = n_before - len(ok)

    ok = ok.assign(event_ts=ok["event_ts"].dt.tz_localize(None),
                   event_date=ok["event_ts"].dt.date.astype(str))
    curated_path = Path(curated)
    if curated_path.exists():  # idempotente: re-ejecutar no duplica datos
        import shutil
        shutil.rmtree(curated_path)
    curated_path.mkdir(parents=True, exist_ok=True)
    ok.to_parquet(curated, partition_cols=["event_date"], index=False)

    Path(rejected).parent.mkdir(parents=True, exist_ok=True)
    rej.astype(str).to_parquet(rejected, index=False)

    stats = {"raw": total, "rejected": len(rej), "duplicates": n_dups, "curated": len(ok)}
    print("ETL:", stats)
    return stats


if __name__ == "__main__":
    run()
