"""Genera eventos sinteticos de producto (simula lo que enviaria una app web/mobile).

Cada usuario recorre un funnel: signup -> onboarding_complete -> feature_used
-> add_to_cart -> purchase, con probabilidades de abandono en cada paso.
Se inyectan duplicados y filas invalidas a proposito para que el ETL tenga
algo real que limpiar.
"""
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_USERS = 5000
DAYS = 60
START = pd.Timestamp("2026-08-01")

# Probabilidad de pasar al siguiente paso del funnel
FUNNEL = [
    ("signup", 1.00),
    ("onboarding_complete", 0.70),
    ("feature_used", 0.80),
    ("add_to_cart", 0.50),
    ("purchase", 0.40),
]
PLATFORMS = ["web", "ios", "android"]
COUNTRIES = ["AR", "MX", "CO", "CL", "ES", "US"]


def _event_id(rng) -> str:
    return str(uuid.UUID(int=int(rng.integers(0, 2**63)) << 64 | int(rng.integers(0, 2**63))))


def generate(out_path: str = "data/raw/events.jsonl") -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = []
    for i in range(N_USERS):
        user_id = f"u_{i:05d}"
        signup_ts = START + pd.Timedelta(days=int(rng.integers(0, DAYS - 30)),
                                         seconds=int(rng.integers(0, 86400)))
        platform = rng.choice(PLATFORMS, p=[0.5, 0.3, 0.2])
        country = rng.choice(COUNTRIES)
        ts = signup_ts
        for step, p in FUNNEL:
            if rng.random() > p:
                break
            rows.append((_event_id(rng), user_id, step, ts, platform, country))
            ts = ts + pd.Timedelta(minutes=int(rng.integers(1, 120)))
        # Actividad recurrente posterior (base de retencion / DAU / MAU)
        retention_p = 0.55 if platform != "web" else 0.40
        for day in (1, 7, 14, 30):
            if rng.random() < retention_p * (0.9 ** (day / 7)):
                visit = signup_ts + pd.Timedelta(days=day, minutes=int(rng.integers(0, 600)))
                rows.append((_event_id(rng), user_id, "session_start", visit, platform, country))

    df = pd.DataFrame(rows, columns=["event_id", "user_id", "event_name",
                                     "event_ts", "platform", "country"])
    df = df[df.event_ts < START + pd.Timedelta(days=DAYS)]

    # Ruido controlado: duplicados y filas invalidas
    dups = df.sample(frac=0.01, random_state=SEED)
    bad = df.sample(frac=0.005, random_state=SEED + 1).copy()
    bad["user_id"] = None
    df = pd.concat([df, dups, bad], ignore_index=True).sample(frac=1, random_state=SEED)
    df["event_ts"] = df["event_ts"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_json(out_path, orient="records", lines=True)
    return df


if __name__ == "__main__":
    d = generate()
    print(f"Generados {len(d):,} eventos en data/raw/events.jsonl")
