import json
import os
import re
from datetime import datetime, timedelta, timezone
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

# ================================
# TOOLS (DIPERBAIKI)
# ================================

def get_current_date_wib():
    tz_wib = timezone(timedelta(hours=7))
    return datetime.now(tz_wib)

def parse_published_date(published_str):
    if not published_str:
        return None
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S%z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%d %b %Y %H:%M:%S %z",
        "%Y-%m-%d %H:%M:%S",
        "%a, %d %b %Y %H:%M:%S",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(published_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except:
            continue
    return None

def days_ago(published_str):
    dt = parse_published_date(published_str)
    if dt is None:
        return 99
    now = datetime.now(timezone.utc)
    delta = now - dt
    return delta.days

def sector_detector(title, summary):
    text = (title + " " + summary).lower()
    sectors = {
        "AI": ["ai", "artificial intelligence", "machine learning", "chatgpt", "claude", "llm", "model"],
        "Space": ["spacex", "space", "rocket", "satellite", "orbit", "starship", "nasa"],
        "Fintech/IPO": ["ipo", "stock", "funding", "venture", "valuation", "billion", "acquisition", "investor"],
        "Regulasi": ["ban", "regulation", "government", "law", "policy", "restriction", "court", "legal"],
        "Startup/VC": ["startup", "venture capital", "seed", "series", "fund", "unicorn", "founder"],
        "Sosial/Media": ["social media", "instagram", "threads", "tiktok", "twitter", "x", "meta", "snap"],
        "Hardware/Deep Tech": ["chip", "semiconductor", "hardware", "robotics", "biotech", "material", "quantum"],
        "Ekonomi/Makro": ["tariff", "debt", "inflation", "economy", "market", "trade", "cbo", "fed"]
    }
    for sector, keywords in sectors.items():
        for kw in keywords:
            if kw in text:
                return sector
    return "Lainnya"

# ================================
# CURATOR CORE
# ================================

def load_articles(filename="news.json"):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_top5(articles, filename="top5.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

def extract_json(text):
    """Ekstrak JSON dari teks yang mungkin mengandung markdown atau teks tambahan."""
    # Coba cari pola JSON array atau objek: [...], {...}
    match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
    if match:
        return match.group(1)
    return text

def curate_top5(all_articles):
    # Siapkan data untuk prompt
    articles_for_prompt = []
    for idx, art in enumerate(all_articles, 1):
        summary_clean = art.get("summary", "").replace('\n', ' ').replace('\r', '')[:300]
        published_str = art.get("published", "")
        days = days_ago(published_str) if published_str else 99
        sector = sector_detector(art['title'], art.get('summary', ''))
        articles_for_prompt.append({
            "id": idx,
            "title": art['title'],
            "summary": summary_clean,
            "published": published_str,
            "days_ago": days,
            "sector": sector,
            "source": art.get('source', '').split('|')[0].strip()
        })

    # ===== PROMPT (TIDAK DIUBAH) =====
    prompt = f"""Anda adalah kurator berita bisnis dan teknologi untuk newsletter "The Quartr" yang berbasis di Indonesia (UTC+7). 
Tugas: pilih 5 berita PALING PENTING dan RELEVAN UNTUK HARI INI dari daftar di bawah.

📌 KRITERIA PENILAIAN (dengan bobot):
1. **Kebaruan (25%)** : Berita yang dipublikasikan dalam 24 jam terakhir (days_ago <= 1) mendapat nilai tinggi. Semakin lama, semakin rendah.
2. **Dampak (25%)** : Nilai transaksi (pendanaan, IPO, akuisisi), jumlah orang terdampak, perubahan pasar/regulasi.
3. **Relevansi Audiens (20%)** : Seberapa relevan untuk eksekutif, investor, dan pelaku startup di Asia Tenggara. Berita tentang Indonesia/ASEAN mendapat nilai tambah.
4. **Potensi Tren (15%)** : Apakah berita ini memicu tren jangka panjang atau hanya kejadian sesaat?
5. **Variasi Sektor (15%)** : Pastikan 5 berita mewakili sektor berbeda (maksimal 2 dari sektor yang sama).

🚫 ATURAN TAMBAHAN:
- Hindari memilih berita yang sudah lebih dari 2 hari (days_ago > 2) kecuali sangat penting.
- Maksimal 1 berita dari sumber yang sama (jangan 2 dari TechCrunch, 2 dari Forbes, dll.)
- Prioritaskan berita yang memiliki data angka (pendanaan, IPO, dll.)

Output: Berikan dalam format JSON **tanpa komentar tambahan**, berupa array of objects dengan field:
{{
  "id": (nomor urut asli),
  "title": (judul asli),
  "summary": (ringkasan asli),
  "link": (url),
  "published": (tanggal),
  "score": (integer 1-5, berdasarkan bobot di atas),
  "reason": (alasan singkat, sebutkan faktor dominan: kebaruan, dampak, atau relevansi)
}}

Berikut daftar berita (format: ID | Sektor | Hari Lalu | Sumber | Judul | Summary):
"""
    for item in articles_for_prompt:
        prompt += f"\n{item['id']} | {item['sector']} | {item['days_ago']} hari | {item['source']} | {item['title']} | {item['summary']}"

    # ===== PANGGIL API =====
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "Anda adalah kurator berita harian yang objektif dan disiplin. Berikan output JSON valid."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    result_text = response.choices[0].message.content

    # ===== LOGGING RAW RESPONSE =====
    print("📝 Raw response dari DeepSeek (500 karakter pertama):")
    print(result_text[:500])
    print("... (sisa dipotong)\n")

    # ===== PARSING YANG LEBIH ROBUST =====
    selected = []
    try:
        # Coba ekstrak JSON dengan regex
        clean_text = extract_json(result_text)
        data = json.loads(clean_text)
        if isinstance(data, dict):
            # Cari array di dalam dict
            if "berita" in data:
                selected = data["berita"]
            elif "articles" in data:
                selected = data["articles"]
            else:
                # Jika tidak ada key, cari nilai pertama yang berupa list
                for value in data.values():
                    if isinstance(value, list):
                        selected = value
                        break
        elif isinstance(data, list):
            selected = data
    except json.JSONDecodeError as e:
        print(f"❌ Gagal parsing JSON: {e}")
        print("🔍 Mencoba parsing alternatif...")
        # Coba cari pola array di seluruh teks
        try:
            # Cari pola seperti [ { ... }, { ... } ]
            match = re.search(r'\[\s*\{.*\}\s*\]', result_text, re.DOTALL)
            if match:
                alt_text = match.group(0)
                data_alt = json.loads(alt_text)
                if isinstance(data_alt, list):
                    selected = data_alt
                    print("✅ Berhasil parsing alternatif (array)")
        except:
            pass

    # Jika selected masih kosong, beri peringatan
    if not selected:
        print("⚠️ Tidak ada data terpilih dari AI. Akan menggunakan fallback.")

    # ===== GABUNGKAN DENGAN DATA ASLI =====
    id_to_original = {i+1: all_articles[i] for i in range(len(all_articles))}
    top5_articles = []
    for item in selected:
        orig = id_to_original.get(item.get("id"))
        if orig:
            article_copy = orig.copy()
            article_copy["score"] = item.get("score", 3)
            article_copy["reason"] = item.get("reason", "")
            top5_articles.append(article_copy)

    # ===== FALLBACK JIKA KURANG DARI 5 =====
    if len(top5_articles) < 5:
        print(f"⚠️ Hanya {len(top5_articles)} artikel terpilih. Menambahkan fallback...")
        selected_titles = [a["title"] for a in top5_articles]
        remaining = [a for a in all_articles if a["title"] not in selected_titles]
        # Urutkan berdasarkan kebaruan
        remaining.sort(key=lambda x: days_ago(x.get("published", "")) if x.get("published") else 99)
        for orig in remaining[:5-len(top5_articles)]:
            article_copy = orig.copy()
            article_copy["score"] = 3
            article_copy["reason"] = "Fallback: berita pelengkap"
            top5_articles.append(article_copy)

    return top5_articles

if __name__ == "__main__":
    print("📖 Membaca news.json...")
    articles = load_articles()
    print(f"Total artikel: {len(articles)}")
    if not articles:
        print("Tidak ada artikel. Keluar.")
        exit(0)
    
    print("🤖 Memilih 5 berita terbaik untuk hari ini...")
    top5 = curate_top5(articles)
    print(f"✅ Terpilih {len(top5)} berita.")
    save_top5(top5)
    print("💾 Disimpan ke top5.json")
    for i, art in enumerate(top5, 1):
        print(f"{i}. {art['title']} - Score: {art.get('score', 'N/A')}")
