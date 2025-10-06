from pathlib import Path
import pandas as pd

EXCEL_PATH = Path("excel/wedago_belanja_master_final.xlsx")
CSV_DIR = Path("csv")
CSV_DIR.mkdir(exist_ok=True, parents=True)

def _save_csv(df: pd.DataFrame, out: Path):
    # Bersihkan NaN -> string kosong agar loader JS aman
    df = df.copy()
    df = df.fillna("")
    # Pastikan semua kolom pakai nama apa adanya (hindari spasi akhir)
    df.columns = [str(c).strip() for c in df.columns]
    df.to_csv(out, index=False, encoding="utf-8", lineterminator="\n")
    print(f"✅ saved {out}")

def main():
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Excel not found: {EXCEL_PATH}")

    xls = pd.ExcelFile(EXCEL_PATH)
    print("📄 sheets:", xls.sheet_names)

    # Peta sheet -> nama file CSV (sesuai Excel kamu)
    sheet_map = {
        "Data": "data.csv",
        "Kategori": "kategori.csv",
        "Promo": "promo.csv",
    }

    for sheet, fname in sheet_map.items():
        if sheet not in xls.sheet_names:
            print(f"⚠️  Sheet '{sheet}' tidak ada. Lewati.")
            continue
        df = pd.read_excel(xls, sheet_name=sheet, engine="openpyxl")

        # Normalisasi ringan khusus sheet "Data"
        if sheet == "Data":
            # pastikan kolom kunci tersedia; jika tidak ada, buat kosong
            needed = [
                "Nama","Deskripsi","Harga","Stok","image_url","action_url","web_url",
                "kategori_pilihan","subcat_primary","subcat_override","Jenis","data_pop"
            ]
            for col in needed:
                if col not in df.columns:
                    df[col] = ""
            # angka -> aman
            for col in ["Harga","Stok","data_pop"]:
                try:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
                except Exception:
                    pass

        _save_csv(df, CSV_DIR / fname)

if __name__ == "__main__":
    main()
