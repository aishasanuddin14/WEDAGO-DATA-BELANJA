# script/split_excel.py
from __future__ import annotations
from pathlib import Path
import pandas as pd

EXCEL_PATH = Path("excel/wedago_belanja_master_final.xlsx")
CSV_DIR = Path("csv")
CSV_DIR.mkdir(exist_ok=True, parents=True)

# Kontrak skema final (URUT WAJIB)
EXPECTED_COLS = [
    "Nama", "Deskripsi", "Harga", "Stok", "image_url", "action_url", "web_url",
    "Toko", "Mitra", "Nama Menu", "Menu", "kategori_pilihan",
    "subcat_primary", "subcat_extra", "subcat_override", "data_pop",
]

SHEET_MAP = {
    "Data": "data.csv",
    "Kategori": "kategori.csv",
    "Promo": "promo.csv",
}

def _save_csv(df: pd.DataFrame, out: Path):
    df = df.copy()
    # Keamanan loader JS: NaN -> "", newline konsisten
    df = df.fillna("")
    # Pastikan header bersih
    df.columns = [str(c).strip() for c in df.columns]
    df.to_csv(out, index=False, encoding="utf-8", lineterminator="\n")
    print(f"✅ saved {out} ({len(df):,} rows)")

def _ensure_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Pastikan semua kolom ada; yang hilang diisi string kosong."""
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    # urutkan sesuai kontrak
    return df[cols]

def _coerce_numeric_int(df: pd.DataFrame, cols: list[str]):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

def _strip_all_strings(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.columns:
        if pd.api.types.is_string_dtype(df[c]) or df[c].dtype == "object":
            df[c] = df[c].astype(str).str.strip()
    return df

def _is_https(url: str) -> bool:
    return isinstance(url, str) and url.startswith("https://")

def main():
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Excel not found: {EXCEL_PATH}")

    # Baca Excel tanpa otak-atik tipe (hindari leading zero hilang)
    xls = pd.ExcelFile(EXCEL_PATH, engine="openpyxl")
    print("📄 sheets:", xls.sheet_names)

    for sheet, fname in SHEET_MAP.items():
        if sheet not in xls.sheet_names:
            print(f"⚠️  Sheet '{sheet}' tidak ada. Lewati.")
            continue

        # Paksa dtype=object agar aman (baru kita normalisasi sendiri)
        df = pd.read_excel(xls, sheet_name=sheet, dtype=object, engine="openpyxl")
        df = _strip_all_strings(df)

        if sheet == "Data":
            # Minimal rename untuk variasi nama kolom umum (opsional)
            rename_map = {
                "NamaMenu": "Nama Menu",
                "Nama_Menu": "Nama Menu",
                "Subcat": "subcat_primary",
                "Subcat Primary": "subcat_primary",
                "Subcat Override": "subcat_override",
            }
            df = df.rename(columns=rename_map)

            # Tambahkan kolom wajib jika hilang, lalu urutkan
            df = _ensure_columns(df, EXPECTED_COLS)

            # Normalisasi angka
            _coerce_numeric_int(df, ["Harga", "Stok", "data_pop"])

            # Aturan bisnis render:
            # - kategori_pilihan == "kuliner"
            # - Produk, bukan Toko: (Harga > 0 atau Stok > 0)
            # - subkategori terisi (override atau primary)
            # - buang baris Jenis == "4" (jika kolom ada)
            jenis_col = "Jenis" if "Jenis" in df.columns else None
            has_sub = (df["subcat_override"] != "") | (df["subcat_primary"] != "")
            is_kuliner = df["kategori_pilihan"].str.lower().eq("kuliner")
            is_product = (df["Harga"].astype(int) > 0) | (df["Stok"].astype(int) > 0)
            not_shop = True
            if jenis_col:
                not_shop = df[jenis_col].astype(str).str.strip() != "4"

            before = len(df)
            df = df[is_kuliner & is_product & has_sub & not_shop].copy()
            after = len(df)
            dropped = before - after

            # Validasi ringan image_url HTTPS (baris non-HTTPS dibuang dengan log)
            bad_img = ~df["image_url"].apply(_is_https)
            bad_cnt = int(bad_img.sum())
            if bad_cnt:
                print(f"⚠️  drop {bad_cnt} rows: image_url non-HTTPS")
                df = df[~bad_img].copy()

            # (Opsional) turunkan nilai data_pop kosong -> 80..99 (random ringan)
            if "data_pop" in df.columns:
                empty_pop = df["data_pop"] == 0
                if int(empty_pop.sum()) > 0:
                    # seed deterministik dari index agar reproducible
                    tmp = ((df.index % 20) + 80)  # 80..99
                    df.loc[empty_pop, "data_pop"] = tmp[empty_pop].astype(int)

            print(f"ℹ️  filtered Data: kept {after:,} rows, dropped {dropped:,}")

            # Jaga urutan & kolom final
            df = df[EXPECTED_COLS]

        # Simpan
        _save_csv(df, CSV_DIR / fname)

if __name__ == "__main__":
    main()
