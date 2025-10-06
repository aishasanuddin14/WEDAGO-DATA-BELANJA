import pandas as pd
from pathlib import Path

excel_path = Path("excel/wedago_belanja_master_final.xlsx")
csv_dir = Path("csv")
csv_dir.mkdir(exist_ok=True)

# Baca semua sheet dari Excel
xls = pd.ExcelFile(excel_path)

# Pastikan nama sheet sama seperti di kuliner (atau ubah kalau beda)
sheet_map = {
    "Data": "data.csv",
    "Kategori": "kategori.csv",
    "Promo": "promo.csv"
}

for sheet, out_name in sheet_map.items():
    if sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df.to_csv(csv_dir / out_name, index=False)
        print(f"✅ Saved {out_name}")
    else:
        print(f"⚠️ Sheet {sheet} not found in Excel.")

