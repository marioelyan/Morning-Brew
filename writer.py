import json
import os
import requests
from openai import OpenAI
from datetime import datetime, timedelta, timezone

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

# ================================
# TOOLS
# ================================

def get_current_date_wib():
    tz_wib = timezone(timedelta(hours=7))
    return datetime.now(tz_wib).strftime("%A, %d %B %Y")

def fetch_asset_image(keyword):
    try:
        url = f"https://api.unsplash.com/photos/random?query={keyword}&orientation=landscape"
        headers = {"Authorization": f"Client-ID {os.environ.get('UNSPLASH_ACCESS_KEY', 'demo')}"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('urls', {}).get('regular', '')
    except:
        pass
    return f"https://source.unsplash.com/featured/?{keyword.replace(' ', ',')}"

def load_top5(filename="top5.json"):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_article(content, filename="Artikel.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

def format_article_text(data, index):
    """Format untuk file .txt (draft mentah)."""
    text = f"📰 ARTIKEL #{index}\n\n"
    text += f"Judul: {data['title']}\n"
    text += f"Subtitle: {data['subtitle']}\n\n"
    text += f"{data['content']}\n\n"
    text += f"Kalimat SEO: {data['seo']}\n"
    text += f"Tags: {data['tags']}\n"
    text += f"Assets (Gambar):\n"
    for asset in data.get('assets', []):
        text += f"- {asset}\n"
    text += "\n" + "="*60 + "\n\n"
    return text

# ================================
# WRITER CORE (DRAFT MENTAH)
# ================================

def write_draft_article(article, index):
    """
    Menghasilkan draft mentah dengan struktur Morning Brew:
    1. TL;DR (Apa yang terjadi)
    2. Dampak (Mengapa ini penting)
    3. Gambaran Besar (Arah tren)
    Gaya: datar, faktual, tanpa opini, tanpa sapaan personal.
    """
    prompt = f"""Anda adalah mesin penulis draft berita dengan gaya **"Datar dan Faktual"** menggunakan bahasa Indonesia yang mudah dipahami dalam pemilihan kata atau kalimat. 
Tulislah draft artikel berdasarkan berita di bawah ini.

📌 **STRUKTUR WAJIB (Morning Brew Style):**
Tulis dalam 3 paragraf yang mengalir, dengan pembagian berikut:
- **Paragraf 1 (TL;DR)**: Apa yang terjadi? Siapa pelakunya? Berapa nilainya? (Fakta mentah).
- **Paragraf 2 (Dampak)**: Mengapa ini penting secara ekonomi/bisnis? Siapa yang terdampak? (Analisis objektif).
- **Paragraf 3 (Gambaran Besar)**: Apa implikasi jangka panjang? Bagaimana tren ke depannya? (Spekulasi berbasis fakta).

📌 **ATURAN KETAT:**
1. **HARAM** menggunakan kata "kamu", "Anda", atau sapaan personal lainnya.
2. **HARAM** menambahkan opini, sindiran, atau kata-kata "menarik", "fantastis", "luar biasa".
3. **HARAM** menggunakan frasa template seperti "Di sisi lain", "Ke depannya", "Tidak hanya... tapi juga".
4. Tulis seperti laporan keuangan: **Kering, Padat, dan Objektif**.
5. Panjang total: 250-300 kata.

📌 **FORMAT OUTPUT (WAJIB JSON):**
{{
  "title": "judul alternatif (tanpa emoticon, max 10 kata)",
  "subtitle": "subtitle singkat (max 15 kata)",
  "content": "teks artikel utuh (250-300 kata) dengan struktur 3 paragraf Morning Brew",
  "seo": "kalimat SEO (1 kalimat, mengandung keyword utama)",
  "tags": "tag1, tag2, tag3, tag4, tag5 (5-7 kata kunci)",
  "assets": ["url_gambar1", "url_gambar2"]
}}

📰 DATA BERITA:
Judul: {article['title']}
Ringkasan: {article.get('summary', '')}
Skor: {article.get('score', 3)}
Alasan: {article.get('reason', '')}
"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "Anda adalah penulis draft berita yang objektif dan datar. Output selalu JSON valid."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,  # rendah agar konsisten dan datar
        response_format={"type": "json_object"}
    )

    try:
        data = json.loads(response.choices[0].message.content)
        if not data.get('assets'):
            keyword = data.get('tags', '').split(',')[0].strip() if data.get('tags') else article['title'][:30]
            data['assets'] = [fetch_asset_image(keyword)]
        # Pastikan semua field ada
        for key in ['title', 'subtitle', 'content', 'seo', 'tags', 'assets']:
            if key not in data:
                data[key] = ""
        return data
    except Exception as e:
        print(f"Gagal parsing JSON untuk artikel {index}: {e}")
        return {
            "title": article['title'],
            "subtitle": "Ringkasan berita hari ini",
            "content": article.get('summary', 'Berita ini penting untuk diikuti.'),
            "seo": article['title'],
            "tags": "berita, teknologi, bisnis",
            "assets": [fetch_asset_image("technology")]
        }

if __name__ == "__main__":
    print("📖 Membaca top5.json...")
    top5 = load_top5()
    if not top5:
        print("Tidak ada top5.json. Jalankan curator dulu.")
        exit(0)

    top5_sorted = sorted(top5, key=lambda x: x.get('score', 0), reverse=True)

    full_archive = f"The Quartr - Newsletter {get_current_date_wib()}\n\n"
    full_archive += "="*50 + "\n\n"

    for idx, article in enumerate(top5_sorted, 1):
        print(f"✍️ Menulis draft mentah artikel #{idx}: {article['title']}")
        data = write_draft_article(article, idx)
        full_archive += format_article_text(data, idx)

    save_article(full_archive, "Artikel.txt")
    print("✅ Artikel.txt (draft mentah) berhasil dibuat.")
