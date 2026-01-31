import pandas as pd
import glob
import os

# Ordnerpfad anpassen
ordner = "errors"

# Alle CSV-Dateien im Ordner finden
dateien = glob.glob(os.path.join(ordner, "*.csv"))

# Liste für gefilterte DataFrames
gefundene_zeilen = []

for datei in dateien:
    df = pd.read_csv(datei)
    
    # Filtern: message == 'x'
    noImgRows = df[df['message'] == 'no images']
    
    if not noImgRows.empty:
        gefundene_zeilen.append([os.path.basename(datei), len(noImgRows)])

df = pd.DataFrame(gefundene_zeilen, columns=["folder", "noImg"])
df = df.sort_values(by="noImg")

print(df[df['noImg'] > 20])