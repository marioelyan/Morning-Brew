import json
import os
import re
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
    text = f"📰 ARTIKEL #{index}\n\n"
    text += f"Judul: {data.get('title', '')}\n"
    text += f"Subtitle: {data.get('subtitle', '')}\n\n"
    text += f"{data.get('content', '')}\n\n"
    text += f"Kalimat SEO: {data.get('seo', '')}\n"
    text += f"Tags: {data.get('tags', '')}\n"
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
    # --- PROMPT (TIDAK DIUBAH) ---
    prompt = f"""Anda adalah mesin penulis draft berita dengan gaya **"Datar dan Faktual"** menggunakan bahasa Indonesia yang mudah dipahami dalam pemilihan kata atau kalimat. 
Tulislah draft artikel berdasarkan berita di bawah ini.

📌 **STRUKTUR WAJIB (Morning Brew Style):**
Tulis dalam 3 paragraf yang mengalir, dengan pembagian berikut:

- **Paragraf 1 (TL;DR)**: 
  Apa yang terjadi? Siapa pelakunya? Berapa nilainya? (Fakta mentah).
  **WAJIB:** Sebutkan angka, nama perusahaan, dan waktu kejadian secara eksplisit.

- **Paragraf 2 (Dampak)**: 
  **Tujuan:** Menjelaskan secara logis dan terstruktur mengapa peristiwa ini penting.
  **WAJIB mengikuti 3 langkah ini secara berurutan:**
  1. **Siapa yang terdampak langsung?** (Perusahaan, industri, konsumen, atau regulator tertentu).
  2. **Apa konsekuensi konkretnya?** (Harga naik/turun, lapangan kerja, akses pasar, regulasi, dll.).
  3. **Mengapa konsekuensi itu penting?** (Hubungkan dengan kepentingan pembaca: biaya, peluang, risiko, atau perubahan kebiasaan).
  **LARANGAN:** Jangan menulis kalimat general seperti "Ini penting karena..." tanpa menyebutkan siapa dan apa dampaknya.

- **Paragraf 3 (Gambaran Besar)**: 
  **Tujuan:** Menempatkan berita dalam konteks tren yang lebih luas, tanpa melompat ke spekulasi liar.
  **WAJIB mengikuti 3 langkah ini secara berurutan:**
  1. **Apa tren global yang sedang terjadi?** (Hubungkan dengan fenomena serupa di industri atau negara lain).
  2. **Apa kemungkinan langkah selanjutnya dari pelaku utama?** (Berdasarkan fakta yang sudah ada, bukan tebakan kosong).
  3. **Apa artinya ini bagi industri/ekosistem dalam 1-2 tahun ke depan?** (Tetap berbasis logika, bukan fiksi).
  **LARANGAN:**
  - Jangan menulis "Ke depannya, kita akan melihat..." tanpa menyebutkan subjek yang jelas.
  - Jangan menulis "Tren ini menunjukkan..." tanpa didukung fakta dari berita.
  - Jangan membuat prediksi yang terlalu jauh (>5 tahun) atau terlalu spekulatif (misal: "Ini bisa mengubah dunia").

📌 **CONTOH PARAGRAF GAMBARAN BESAR YANG BAIK (Referensi):**
--- MULAI CONTOH ---
"Langkah Amazon ini sejalan dengan tren perusahaan cloud besar yang mulai mengembangkan chip sendiri. Google dan Microsoft juga telah melakukannya. Ke depannya, persaingan di pasar chip AI kemungkinan akan semakin ketat, dengan harga yang lebih kompetitif dan lebih banyak pilihan bagi konsumen. Dalam 1-2 tahun ke depan, kita mungkin melihat Nvidia mulai merespons dengan strategi harga atau inovasi baru."
--- AKHIR CONTOH ---

📌 **CONTOH PARAGRAF DAMPAK YANG BAIK (Referensi):**
--- MULAI CONTOH ---
"Langkah ini langsung memengaruhi ekosistem startup AI di Asia. Startup yang selama ini bergantung pada chip Nvidia dengan harga mahal kini punya alternatif dari Amazon yang lebih murah. Biaya pengembangan AI bisa turun 20-30%, yang berarti lebih banyak startup bisa mengakses teknologi ini. Bagi investor, ini juga sinyal bahwa persaingan di pasar chip AI mulai memanas."
--- AKHIR CONTOH ---

📌 **ATURAN KETAT:**
1. **HARAM** menggunakan kata "kamu", "Anda", atau sapaan personal lainnya.
2. **HARAM** menambahkan opini, sindiran, atau kata-kata "menarik", "fantastis", "luar biasa".
3. **HARAM** menggunakan frasa template seperti "Di sisi lain", "Ke depannya", "Tidak hanya... tapi juga".
4. **HARAM** memulai paragraf dampak dengan "Ini penting karena..." atau "Hal ini berdampak..." tanpa menyebut subjek spesifik.
5. **HARAM** memulai paragraf gambaran besar dengan "Tren ini menunjukkan..." tanpa didukung fakta.
6. Tulis seperti laporan keuangan: **Kering, Padat, dan Objektif**, tapi tetap **logis dan terstruktur**.
7. Panjang total: 250-300 kata.

📰 DATA BERITA:
Judul: {article['title']}
Ringkasan: {article.get('summary', '')}
Skor: {article.get('score', 3)}
Alasan: {article.get('reason', '')}
"""
    # --- PANGGIL API (tanpa response_format) ---
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Anda adalah penulis draft berita yang objektif dan datar. Output selalu JSON valid."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
    except Exception as e:
        print(f"❌ API error untuk artikel {index}: {e}")
        return {
            "title": article.get('title', 'Berita tanpa judul'),
            "subtitle": "Ringkasan berita",
            "content": article.get('summary', 'Konten tidak tersedia.'),
            "seo": article.get('title', ''),
            "tags": "berita, teknologi, bisnis",
            "assets": [fetch_asset_image("technology")]
        }

    raw = response.choices[0].message.content
    print(f"📝 Raw response artikel #{index} (200 karakter pertama): {raw[:200]}...")

    # --- PARSING JSON (manual + regex) ---
    data = None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Cari pola JSON {...} di tengah teks
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                pass

    # --- FALLBACK jika parsing gagal ---
    if data is None:
        print(f"❌ Gagal parsing JSON untuk artikel {index}. Gunakan fallback.")
        return {
            "title": article.get('title', 'Berita tanpa judul'),
            "subtitle": "Ringkasan berita",
            "content": article.get('summary', 'Konten tidak tersedia.'),
            "seo": article.get('title', ''),
            "tags": "berita, teknologi, bisnis",
            "assets": [fetch_asset_image("technology")]
        }

    # --- PASTIKAN SEMUA FIELD ADA ---
    if not data.get('assets'):
        keyword = data.get('tags', '').split(',')[0].strip() if data.get('tags') else article['title'][:30]
        data['assets'] = [fetch_asset_image(keyword)]

    for key in ['title', 'subtitle', 'content', 'seo', 'tags', 'assets']:
        if key not in data or not data[key]:
            if key == 'title':
                data[key] = article.get('title', 'Berita tanpa judul')
            elif key == 'content':
                data[key] = article.get('summary', 'Konten tidak tersedia.')
            elif key == 'subtitle':
                data[key] = "Ringkasan berita"
            elif key == 'seo':
                data[key] = article.get('title', '')
            elif key == 'tags':
                data[key] = "berita, teknologi, bisnis"
            elif key == 'assets':
                data[key] = [fetch_asset_image("technology")]

    return data

if __name__ == "__main__":
    print("📖 Membaca top5.json...")
    top5 = load_top5()
    if not top5:
        print("Tidak ada top5.json. Jalankan curator dulu.")
        exit(0)

    print(f"✅ {len(top5)} artikel ditemukan di top5.json.")

    top5_sorted = sorted(top5, key=lambda x: x.get('score', 0), reverse=True)

    full_archive = f"The Quartr - Newsletter {get_current_date_wib()}\n\n"
    full_archive += "="*50 + "\n\n"

    for idx, article in enumerate(top5_sorted, 1):
        print(f"✍️ Menulis draft mentah artikel #{idx}: {article.get('title', 'TANPA JUDUL')}")
        data = write_draft_article(article, idx)
        full_archive += format_article_text(data, idx)

    save_article(full_archive, "Artikel.txt")
    print("✅ Artikel.txt (draft mentah) berhasil dibuat.")
