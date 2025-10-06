# validators/validate_csv.py
import csv, sys, pathlib, re

BASE = pathlib.Path("csv")

# =========================
# Skema per file
# =========================
DATA_EXPECTED = [
    "Nama","Deskripsi","Harga","Stok","image_url","action_url","web_url",
    "Toko","Mitra","Nama Menu","Menu","kategori_pilihan",
    "subcat_primary","subcat_extra","subcat_override","data_pop"
]

# Dari log kamu, sheet Kategori menghasilkan header berikut.
KATEGORI_REQUIRED = ["subcat_code", "label"]
KATEGORI_OPTIONAL = ["emoji", "action_url"]
KATEGORI_ALLOWED  = KATEGORI_REQUIRED + KATEGORI_OPTIONAL

# Promo: biarkan fleksibel, tapi kalau kolom ada, kita validasi isinya.
PROMO_OPTIONAL = ["title", "subtitle", "image_url", "action_url", "active", "start_date", "end_date"]

# =========================
# Util
# =========================
def ensure_https(u: str) -> bool:
    return isinstance(u, str) and u.startswith("https://")

def ensure_action(u: str) -> bool:
    # ijinkan action://..., https://..., http://... (kalau ada)
    return (isinstance(u, str) and (u.startswith("action://") or u.startswith("https://") or u.startswith("http://"))) or (u == "")

def read_csv(path: pathlib.Path):
    if not path.exists():
        raise SystemExit(f"❌ Missing file: {path}")
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)

# =========================
# Validator: data.csv
# =========================
def validate_data_csv():
    p = BASE / "data.csv"
    headers, rows = read_csv(p)

    if headers != DATA_EXPECTED:
        raise SystemExit(f"❌ Kolom mismatch untuk data.csv.\nDapat : {headers}\nHarus: {DATA_EXPECTED}")

    bad = []
    for idx, row in enumerate(rows, start=2):  # baris data mulai 2
        # angka murni
        harga = row["Harga"]
        stok  = row["Stok"]
        if not str(harga).isdigit():
            bad.append((idx, "Harga bukan integer"))
        if stok and not str(stok).isdigit():
            bad.append((idx, "Stok bukan integer/empty"))

        # aturan bisnis (hanya jika baris kuliner)
        is_kuliner = str(row["kategori_pilihan"]).strip().lower() == "kuliner"
        sub_ok = bool(row["subcat_override"] or row["subcat_primary"])
        try:
            harga_i = int(harga) if str(harga).isdigit() else 0
            stok_i  = int(stok) if str(stok).isdigit() else 0
        except Exception:
            harga_i, stok_i = 0, 0

        prod_ok = ((harga_i > 0) or (stok_i > 0)) and sub_ok

        if not ensure_https(row["image_url"]):
            bad.append((idx, "image_url wajib HTTPS"))

        if is_kuliner and not prod_ok:
            bad.append((idx, "baris kuliner tidak memenuhi (Harga/Stok/Subkategori)"))

    if bad:
        msg = "\n".join(f"Baris {ln}: {m}" for ln, m in bad[:80])
        raise SystemExit(f"❌ VALIDASI data.csv GAGAL ({len(bad)} masalah)\n{msg}")

    print("✅ data.csv valid")

# =========================
# Validator: kategori.csv
# =========================
def validate_kategori_csv():
    p = BASE / "kategori.csv"
    headers, rows = read_csv(p)

    # cek tidak ada header duplikat
    if len(headers) != len(set(headers)):
        raise SystemExit(f"❌ kategori.csv memiliki header duplikat: {headers}")

    # wajib minimal kolom kunci
    missing = [c for c in KATEGORI_REQUIRED if c not in headers]
    if missing:
        raise SystemExit(f"❌ kategori.csv kolom wajib hilang: {missing}\nDapat: {headers}\nDiizinkan: {KATEGORI_ALLOWED}")

    # kolom selain yang diizinkan tetap boleh, tapi beri peringatan ringan (tidak menggagalkan)
    extra = [c for c in headers if c not in KATEGORI_ALLOWED]
    if extra:
        print(f"ℹ️  kategori.csv memiliki kolom tambahan (ok): {extra}")

    bad = []
    for idx, row in enumerate(rows, start=2):
        code = str(row.get("subcat_code","")).strip()
        label = str(row.get("label","")).strip()
        emoji = str(row.get("emoji","")).strip() if "emoji" in headers else ""
        aurl  = str(row.get("action_url","")).strip() if "action_url" in headers else ""

        if not code:
            bad.append((idx, "subcat_code kosong"))
        # batasan ringan: lowercase huruf/angka/_- dan tanpa spasi
        if code and not re.fullmatch(r"[a-z0-9_\-]+", code):
            bad.append((idx, "subcat_code hanya boleh [a-z0-9_-]"))

        if not label:
            bad.append((idx, "label kosong"))

        # emoji opsional; kalau ada, panjang 1–3 codepoints (heuristik longgar)
        if emoji and len(emoji) > 5:
            bad.append((idx, "emoji terlalu panjang (opsional)"))

        if "action_url" in headers and not ensure_action(aurl):
            bad.append((idx, "action_url invalid (boleh kosong, action://, http://, https://)"))

    if bad:
        msg = "\n".join(f"Baris {ln}: {m}" for ln, m in bad[:80])
        raise SystemExit(f"❌ VALIDASI kategori.csv GAGAL ({len(bad)} masalah)\n{msg}")

    print("✅ kategori.csv valid")

# =========================
# Validator: promo.csv
# =========================
def validate_promo_csv():
    p = BASE / "promo.csv"
    headers, rows = read_csv(p)

    # Tidak memaksa skema kaku. Cek dasar: tidak kosong & header unik.
    if not headers:
        raise SystemExit("❌ promo.csv tidak memiliki header.")
    if len(headers) != len(set(headers)):
        raise SystemExit(f"❌ promo.csv memiliki header duplikat: {headers}")

    # Validasi ringan bila kolom ada
    bad = []
    for idx, row in enumerate(rows, start=2):
        img = row.get("image_url", "")
        act = row.get("action_url", "")
        if "image_url" in headers and img and not ensure_https(img):
            bad.append((idx, "image_url harus HTTPS bila diisi"))
        if "action_url" in headers and act and not ensure_action(act):
            bad.append((idx, "action_url invalid (action://, http://, https://)"))

        # active -> boolean numerik 0/1 kalau ada
        if "active" in headers:
            val = str(row.get("active","")).strip()
            if val not in ("", "0", "1", "true", "false", "True", "False"):
                bad.append((idx, "active harus 0/1/true/false bila diisi"))

    if bad:
        msg = "\n".join(f"Baris {ln}: {m}" for ln, m in bad[:80])
        raise SystemExit(f"❌ VALIDASI promo.csv GAGAL ({len(bad)} masalah)\n{msg}")

    print("✅ promo.csv valid")

# =========================
# Main
# =========================
if __name__ == "__main__":
    validate_data_csv()
    validate_kategori_csv()
    validate_promo_csv()
    print("🎉 Semua CSV valid")
