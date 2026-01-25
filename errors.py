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
    treffer = df[df['message'] == 'no images']
    
    if not treffer.empty:
        print(f"Treffer in Datei: {os.path.basename(datei)}")
        print(treffer)
        print("-" * 40)

