
from pathlib import Path
import pandas as pd

DATA_PATH = Path("data/du_lieu_B2.csv")

# Doc du lieu
df = pd.read_csv(DATA_PATH)

print("=== 1. THONG TIN DU LIEU ===")
print("So ban ghi:", len(df))
print("Danh sach cot:", df.columns.tolist())

print("\n=== 2. KIEM TRA CAC COT BAT BUOC ===")
required = [
    "timestamp",
    "temperature",
    "humidity",
    "distance_cm"
]

missing = [c for c in required if c not in df.columns]

if missing:
    raise ValueError(f"Thieu cot bat buoc: {missing}")

# Chuyen timestamp
df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    utc=True,
    errors="coerce"
)

# Chuyen cac kenh cam bien sang so
for col in required[1:]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

print("\n=== 3. GIA TRI THIEU ===")
print(df[required].isna().sum())

# Sap xep thoi gian
df = df.sort_values("timestamp").reset_index(drop=True)

print("\n=== 4. THOI GIAN ===")
print("Bat dau:", df["timestamp"].min())
print("Ket thuc:", df["timestamp"].max())

# Khoang cach giua hai ban ghi
interval = df["timestamp"].diff().dt.total_seconds()

print("\n=== 5. CHU KY THU DU LIEU ===")
print(interval.describe())
print("So khoang > 5 giay:", (interval > 5).sum())
print("So timestamp trung:", df["timestamp"].duplicated().sum())

print("\n=== 6. THONG KE CAM BIEN ===")
print(df[["temperature", "humidity", "distance_cm"]].describe())

print("\n=== 7. NAM BAN GHI DAU ===")
print(df.head())

print("\n=== HOAN THANH KIEM TRA ===")
