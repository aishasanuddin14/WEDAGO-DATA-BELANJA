# validators/validate_csv.py
import csv, sys, pathlib

EXPECTED = ["Nama","Deskripsi","Harga","Stok","image_url","action_url","web_url",
            "Toko","Mitra","Nama Menu","Menu","kategori_pilihan",
            "subcat_primary","subcat_extra","subcat_override","data_pop"]

def ensure_https(u): return isinstance(u, str) and u.startswith("https://")

def check(path):
    p = pathlib.Path(path)
    if not p.exists():
        raise SystemExit(f"❌ Missing file: {p}")

    bad = []
    with p.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if r.fieldnames != EXPECTED:
            raise SystemExit(f"❌ Kolom mismatch.\nDapat  : {r.fieldnames}\nHarus : {EXPECTED}")
        for i, row in enumerate(r, 2):  # +1 header, baris data mulai 2
            # angka murni
            if not str(row["Harga"]).isdigit():
                bad.append((i, "Harga bukan integer"))
            if row["Stok"] and not str(row["Stok"]).isdigit():
                bad.append((i, "Stok bukan integer/empty"))

            # aturan bisnis produk
            has_sub = (row["subcat_override"] or row["subcat_primary"])
            is_kuliner = str(row["kategori_pilihan"]).strip().lower() == "kuliner"
            harga = int(row["Harga"]) if str(row["Harga"]).isdigit() else 0
            stok  = int(row["Stok"]) if str(row["Stok"]).isdigit() else 0
            prod_ok = ((harga > 0) or (stok > 0)) and has_sub

            if not ensure_https(row["image_url"]):
                bad.append((i, "image_url wajib HTTPS"))
            if is_kuliner and not prod_ok:
                bad.append((i, "baris kuliner tidak memenuhi (Harga/Stok/Subkategori)"))

    if bad:
        msg = "\n".join(f"Baris {ln}: {m}" for ln, m in bad[:50])
        raise SystemExit(f"❌ VALIDASI GAGAL ({len(bad)} masalah)\n{msg}")
    print(f"✅ {path} valid")

if __name__ == "__main__":
    base = pathlib.Path("csv")
    for fn in ["data.csv","kategori.csv","promo.csv"]:
        check(base / fn)
