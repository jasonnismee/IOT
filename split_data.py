
from pathlib import Path
import pandas as pd

INPUT = Path("data/du_lieu_B3_5s.csv")
OUT_DIR = Path("data")
OUT_DIR.mkdir(exist_ok=True)

df = pd.read_csv(INPUT)
df["timestamp"] = pd.to_datetime(
    df["timestamp"], utc=True
)

df = df.sort_values("timestamp").reset_index(drop=True)

# Chia 70% theo thu tu thoi gian
cut_idx = int(len(df) * 0.7)

train = df.iloc[:cut_idx].copy()
test = df.iloc[cut_idx:].copy()

# Moc cat: thoi diem dau tien cua test
cut_time = test["timestamp"].min()

# Kiem tra khong chong lan
assert train["timestamp"].max() < cut_time

train.to_csv(OUT_DIR / "train_5s.csv", index=False)
test.to_csv(OUT_DIR / "test_5s.csv", index=False)

print("=== CHIA TRAIN / TEST ===")
print("Tong so dong:", len(df))
print("Train:", len(train))
print("Test:", len(test))

print("\n=== RANH GIOI THOI GIAN ===")
print("Train bat dau:", train["timestamp"].min())
print("Train ket thuc:", train["timestamp"].max())
print("Test bat dau:", test["timestamp"].min())
print("Test ket thuc:", test["timestamp"].max())

print("\n=== DU LIEU THIEU ===")
for name, part in [("TRAIN", train), ("TEST", test)]:
    print(f"\n{name}")
    print(
        part[["temperature", "humidity", "distance_cm"]]
        .isna().sum()
    )

print("\nDa luu train_5s.csv va test_5s.csv")
