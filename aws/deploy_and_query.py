"""Sube la capa curated a S3 y corre las queries SQL en Athena (boto3).

Requisitos: credenciales AWS configuradas y el stack de aws/template.yaml desplegado:
  aws cloudformation deploy --template-file aws/template.yaml --stack-name product-analytics
Uso:
  python aws/deploy_and_query.py --bucket <BucketName del stack>
"""
import argparse
import time
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parent.parent


def upload_curated(s3, bucket: str):
    base = ROOT / "data/curated/events"
    files = list(base.rglob("*.parquet"))
    for f in files:
        key = "curated/events/" + f.relative_to(base).as_posix()
        s3.upload_file(str(f), bucket, key)
    print(f"Subidos {len(files)} archivos a s3://{bucket}/curated/events/")


def run_query(athena, sql: str, workgroup: str) -> list:
    qid = athena.start_query_execution(
        QueryString=sql, WorkGroup=workgroup,
        QueryExecutionContext={"Database": "product_analytics"})["QueryExecutionId"]
    while True:
        state = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(1)
    if state != "SUCCEEDED":
        raise RuntimeError(f"Query {qid} termino en {state}")
    rows = athena.get_query_results(QueryExecutionId=qid)["ResultSet"]["Rows"]
    return [[c.get("VarCharValue") for c in r["Data"]] for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--workgroup", default="product-analytics-wg")
    ap.add_argument("--region", default="us-east-1")
    args = ap.parse_args()

    s3 = boto3.client("s3", region_name=args.region)
    athena = boto3.client("athena", region_name=args.region)
    upload_curated(s3, args.bucket)

    for f in sorted((ROOT / "sql").glob("*.sql")):
        rows = run_query(athena, f.read_text(), args.workgroup)
        print(f"\n=== {f.stem} ===")
        for r in rows[:8]:
            print(r)


if __name__ == "__main__":
    main()
