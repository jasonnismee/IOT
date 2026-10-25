
import pandas as pd

df = pd.read_csv("data/du_lieu_B2.csv")

df["timestamp"] = pd.to_datetime(
    df["timestamp"], utc=True
)

df = df.sort_values("timestamp").reset_index(drop=True)

# Khoang thoi gian giua cac ban ghi
df["gap_s"] = df["timestamp"].diff().dt.total_seconds()

# Phat hien reset va mat ket noi dai
df["reset_sequence"] = df["sequence"].diff() < 0
df["reset_uptime"] = df["uptime_s"].diff() < 0
df["long_gap"] = df["gap_s"] > 20

# Danh dau cac doan lien tuc
df["new_segment"] = (
    df["reset_sequence"]
    | df["reset_uptime"]
    | df["long_gap"]
)

df["segment_id"] = df["new_segment"].cumsum() + 1

print("=== KIEM TRA DOAN DU LIEU ===")
print("Tong ban ghi:", len(df))
print("So khoang > 20 giay:", df["long_gap"].sum())
print("So lan reset sequence:", df["reset_sequence"].sum())
print("So lan reset uptime:", df["reset_uptime"].sum())
print("So doan lien tuc:", df["segment_id"].nunique())

print("\n=== THONG KE TUNG DOAN ===")
summary = df.groupby("segment_id").agg(
    count=("timestamp", "count"),
    start=("timestamp", "min"),
    end=("timestamp", "max"),
)
print(summary.to_string())

print("\n=== KIEM TRA NHAN NHIET DO ===")
if "temperature_observed" in df.columns:
    print(df["temperature_observed"].value_counts(dropna=False))
else:
    print("Khong co cot temperature_observed")

print("\n=== NGUON DU LIEU ===")
if "data_source" in df.columns:
    print(df["data_source"].value_counts(dropna=False))

print("\nHoan thanh!")
