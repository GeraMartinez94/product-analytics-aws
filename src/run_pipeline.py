"""Orquesta todo en local: generar -> ETL -> SQL (DuckDB) -> resultados en CSV.

DuckDB lee el Parquet curated igual que Athena lo leeria desde S3, asi que
las mismas queries SQL sirven en ambos lados.
"""
from pathlib import Path

import duckdb

import etl
import generate_events

ROOT = Path(__file__).resolve().parent.parent


def main():
    generate_events.generate(str(ROOT / "data/raw/events.jsonl"))
    etl.run(str(ROOT / "data/raw/events.jsonl"), str(ROOT / "data/curated/events"),
            str(ROOT / "data/rejected/events.parquet"))

    con = duckdb.connect()
    con.execute(f"""
        CREATE VIEW events AS
        SELECT * FROM read_parquet('{ROOT}/data/curated/events/*/*.parquet', hive_partitioning=true)
    """)
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    for f in sorted((ROOT / "sql").glob("*.sql")):
        df = con.execute(f.read_text()).df()
        df.to_csv(out / f"{f.stem}.csv", index=False)
        print(f"\n=== {f.stem} ===")
        print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
