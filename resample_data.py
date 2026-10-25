
from pathlib import Path
import numpy as np
import pandas as pd

INPUT = Path("data/du_lieu_B2.csv")
OUTPUT = Path("data/du_lieu_B3_5s.csv")

df = pd.read_csv(INPUT)

df["timestamp"] = pd.to_datetime(
    df["timestamp"], utc=True, errors="coerce"
)

df = df.sort_values("timestamp").reset_index(drop=True)

channels = ["temperature", "humidity", "distance_cm"]

for col in channels:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Kiem tra dau vao
assert df["timestamp"].notna().all()
assert not df["timestamp"].duplicated().any()

# Tao segment dua tren gap va reset
gap = df["timestamp"].diff().dt.total_seconds()

reset_seq = (
    df["sequence"].diff() < 0
    if "sequence" in df else False
)

reset_uptime = (
    df["uptime_s"].diff() < 0
    if "uptime_s" in df else False
)

df["segment_id"] = (
    (gap > 20) | reset_seq | reset_uptime
).cumsum() + 1

# Danh dau gia tri nhiet do quan sat
if "temperature_observed" not in df:
    df["temperature_observed"] = 1

df["temperature_observed"] = (
    pd.to_numeric(df["temperature_observed"], errors="coerce")
    .fillna(0)
    .astype(int)
)

# Khoi tao luoi 5 giay cho tung segment
results = []

for segment_id, part in df.groupby("segment_id"):
    part = part.copy().set_index("timestamp")

    # Goc luoi la moc 5s gan nhat
    origin = part.index.min().round("5s")

    # Anh xa mau vao cac bin 5 giay
    offset = (
        (part.index - origin).total_seconds() / 5
    )
    bin_index = np.rint(offset).astype(int)

    part["grid_time"] = (
        origin + pd.to_timedelta(bin_index * 5, unit="s")
    )

    # Neu nhieu mau cung bin, lay trung binh
    grouped = part.groupby("grid_time")[channels].mean()

    # Chi nhan nhiet do la quan sat khi bin
    # chua it nhat mot gia tri goc hop le
    observed = part.assign(
        valid_temp=(
            part["temperature"].notna()
            & part["temperature_observed"].eq(1)
        )
    ).groupby("grid_time")["valid_temp"].any()

    full_index = pd.date_range(
        grouped.index.min(),
        grouped.index.max(),
        freq="5s",
        tz="UTC"
    )

    grouped = grouped.reindex(full_index)
    observed = observed.reindex(full_index, fill_value=False)

    grouped["temperature_observed"] = observed.astype(int)
    grouped["segment_id"] = segment_id

    results.append(grouped)

out = pd.concat(results).reset_index()
out = out.rename(columns={"index": "timestamp"})

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUTPUT, index=False)

print("=== RESAMPLE 5 GIAY ===")
print("So dong goc:", len(df))
print("So dong sau resample:", len(out))
print("So segment:", out["segment_id"].nunique())

print("\nGia tri thieu:")
print(out[channels].isna().sum())

print("\nNhiet do quan sat:")
print(out["temperature_observed"].value_counts())

print("\nDu lieu dau:")
print(out.head(15).to_string(index=False))

print("\nDa luu:", OUTPUT)
