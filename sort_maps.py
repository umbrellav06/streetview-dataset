import pandas as pd
from huggingface_hub import list_repo_files
from collections import defaultdict

repo_id = "charlottev/google-streetview-images-by-country"

files = list_repo_files(repo_id, repo_type="dataset")

counts = defaultdict(int)

for f in files:
    parts = f.split("/")
    if len(parts) > 1:
        folder = parts[-2]   # letzter Ordnername
    else:
        folder = "."         # falls Datei direkt im Root liegt
    counts[folder] += 1


df = pd.DataFrame(list(counts.items()), columns=["folder", "number"])
folder_counts = df.sort_values(by="number")

print("folder_counts fertig")

maps = pd.read_csv("maps.csv")

order = folder_counts["folder"].tolist()

# Sortierschlüssel erzeugen
maps["sort_key"] = maps["country"].apply(lambda x: order.index(x) if x in order else 999999)

maps_sorted = maps.sort_values("sort_key").drop(columns="sort_key")

maps_sorted.to_csv("maps.csv", index=False)

print("maps.csv aktualisiert")
