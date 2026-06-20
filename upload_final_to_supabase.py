import os
import re
import sys
from datetime import datetime
from supabase import create_client

# ========================================
# 1. AMBIL CREDENTIAL DARI ENVIRONMENT
# ========================================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL:
    print("❌ SUPABASE_URL tidak ditemukan di environment.")
    sys.exit(1)

if not SUPABASE_KEY:
    print("❌ SUPABASE_SERVICE_ROLE_KEY tidak ditemukan di environment.")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
print("✅ Koneksi ke Supabase berhasil.")


# ========================================
# 2. EKSTRAK TANGGAL DARI FILE
# ========================================

def extract_published_date(content):
    """
    Mencari pola: *The Quartr — Saturday, 20 June 2026*
    Mengembalikan string YYYY-MM-DD, atau None jika gagal.
    """
    match = re.search(r'\*The Quartr — (.*?)\*', content)
    if not match:
        return None

    date_string = match.group(1).strip()
    try:
        parsed_date = datetime.strptime(date_string, "%A, %d %B %Y")
        return parsed_date.strftime("%Y-%m-%d")
    except ValueError as e:
        print(f"⚠️ Gagal parsing tanggal: '{date_string}'. Error: {e}")
        return None


# ========================================
# 3. PARSE FILE final_edition.txt
# ========================================

def parse_final_edition(filename="final_edition.txt"):
    """
    Membaca file final_edition.txt dan mengekstrak:
    - title   : dari 📰 **...**
    - hook    : dari ## 🎯 The Hook
    - pojok   : dari ## 🧠 Pojok 90 derajat
    - bonding : dari ## 🎮 Bonding
    - content : seluruh teks
    - published_date : dari header
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ File {filename} tidak ditemukan.")
        return None

    if not content.strip():
        print("❌ File kosong.")
        return None

    # === Ekstrak Judul ===
    title_match = re.search(r'📰 \*\*(.*?)\*\*', content)
    title = title_match.group(1).strip() if title_match else ""

    # === Ekstrak Hook ===
    hook_match = re.search(r'## 🎯 The Hook\n(.*?)\n\n📌', content, re.DOTALL)
    hook = hook_match.group(1).strip() if hook_match else ""

    # === Ekstrak Pojok 90 derajat ===
    pojok_match = re.search(r'## 🧠 Pojok 90 derajat\n(.*?)\n\n## 🎮', content, re.DOTALL)
    pojok = pojok_match.group(1).strip() if pojok_match else ""

    # === Ekstrak Bonding ===
    bonding_match = re.search(r'## 🎮 Bonding\n(.*?)\n\n## 📌', content, re.DOTALL)
    bonding = bonding_match.group(1).strip() if bonding_match else ""

    # === Ekstrak Tanggal ===
    published_date = extract_published_date(content)

    return {
        "title": title,
        "content": content,
        "hook": hook,
        "pojok": pojok,
        "bonding": bonding,
        "published_date": published_date
    }


# ========================================
# 4. UPLOAD KE SUPABASE
# ========================================

def upload_final_edition(data, published_date):
    """
    Upload edisi final ke Supabase.
    Jika published_date None, gunakan hari ini sebagai fallback.
    """
    if not published_date:
        published_date = datetime.now().strftime("%Y-%m-%d")
        print(f"⚠️ Tanggal tidak ditemukan di file. Gunakan hari ini: {published_date}")

    # Cek apakah sudah ada edisi untuk tanggal ini
    existing = supabase.table("final_editions") \
        .select("id") \
        .eq("published_date", published_date) \
        .execute()

    row = {
        "published_date": published_date,
        "title": data["title"],
        "content": data["content"],
        "hook": data["hook"],
        "quarter_time": data["pojok"],      # Nama kolom tetap quarter_time
        "quiz": data["bonding"],            # Nama kolom tetap quiz
        "updated_at": datetime.now().isoformat()
    }

    try:
        if existing.data:
            supabase.table("final_editions") \
                .update(row) \
                .eq("published_date", published_date) \
                .execute()
            print(f"✅ Edisi {published_date} berhasil diUPDATE di Supabase.")
        else:
            supabase.table("final_editions") \
                .insert(row) \
                .execute()
            print(f"✅ Edisi {published_date} berhasil diINSERT ke Supabase.")
        return True
    except Exception as e:
        print(f"❌ Gagal upload: {e}")
        return False


# ========================================
# 5. MAIN
# ========================================

if __name__ == "__main__":
    print("📖 Membaca final_edition.txt...")
    data = parse_final_edition("final_edition.txt")

    if not data:
        print("❌ Gagal parsing. Pastikan file final_edition.txt ada dan sesuai format.")
        sys.exit(1)

    if not data["title"]:
        print("⚠️ Judul tidak ditemukan. Upload tetap dilanjutkan.")
    else:
        print(f"📌 Judul: {data['title'][:60]}...")

    if data["published_date"]:
        print(f"📅 Tanggal dari file: {data['published_date']}")
    else:
        print("⚠️ Tanggal tidak ditemukan di file. Akan menggunakan tanggal hari ini.")

    print(f"📝 Panjang konten: {len(data['content'])} karakter")
    print("📤 Mengupload ke Supabase...")

    success = upload_final_edition(data, data["published_date"])

    if success:
        print("✅ Selesai.")
        sys.exit(0)
    else:
        print("❌ Upload gagal.")
        sys.exit(1)
