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
    """
    Mencari gambar gratis dari Unsplash berdasarkan keyword.
    Jika gagal, berikan fallback URL.
    """
    try:
        url = f"https://api.unsplash.com/photos/random?query={keyword}&orientation=landscape"
        headers = {
            "Authorization": f"Client-ID {os.environ.get('UNSPLASH_ACCESS_KEY', 'demo')}"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('urls', {}).get('regular', '')
    except:
        pass
    # Fallback
    return f"https://source.unsplash.com/featured/?{keyword.replace(' ', ',')}"

def load_top5(filename="top5.json"):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_article(content, filename="Artikel.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

def send_to_telegram(text):
    import subprocess
    if len(text) > 4096:
        text = text[:4093] + "..."
    subprocess.run([
        "curl", "-s", "-X", "POST",
        f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
        "-F", f"chat_id={os.environ['TELEGRAM_CHAT_ID']}",
        "-F", f"text={text}",
        "-F", "parse_mode=Markdown"
    ])

# ================================
# WRITER CORE
# ================================

def write_full_article(article, index):
    """
    Menghasilkan artikel lengkap dengan framework 4A untuk satu berita.
    Output: dict dengan judul, subjudul, konten, seo, tags, assets.
    """
    prompt = f"""Anda adalah penulis senior untuk newsletter "The Quartr" yang berbasis di Indonesia.

Tugas: Tulislah artikel berita (300-400 kata) berdasarkan berita di bawah ini dengan mengikuti **Framework 4A**:

1. **Alert (Peringatan)**: Paragraf pembuka yang menarik perhatian. Bisa berupa pertanyaan retoris, fakta mengejutkan, atau pernyataan berani yang menggugah rasa penasaran.
2. **Analysis (Analisis)**: Jelaskan mengapa berita ini penting. Berikan analisis dampak secara **makro** (pasar, regulasi, ekonomi) dan **mikro** (startup, founder, investor).
3. **Angle (Sudut Pandang)**: Sajikan sudut pandang unik yang relevan untuk pembaca umum. Anggap pembaca adalah orang yang cerdas tapi bukan ahli di bidang ini. Buat mereka merasa "ini penting buat saya".
4. **Action (Ajakan)**: Akhiri dengan ajakan atau pertanyaan reflektif yang sesuai dengan isi berita (bisa ajakan diskusi, pantau perkembangan, atau refleksi).

📌 FORMAT OUTPUT (WAJIB):
- **Judul Alternatif**: Judul baru yang lebih menarik, sesuai dengan sudut pandang artikel. Tanpa emoticon, maksimal 10 kata.
- **Subtitle**: 1 kalimat (maks 15 kata) yang merangkum esensi berita.
- **Konten**: 300-400 kata, terdiri dari paragraf-paragraf yang mengalir (Alert → Analysis → Angle → Action). Hindari subjudul, bullet points, atau markdown.
- **Kalimat SEO**: 1 kalimat yang mengandung keyword utama, untuk optimasi mesin pencari.
- **Tag**: 5-7 kata kunci (misal: SpaceX, IPO, Startup, Teknologi, Investasi) dipisahkan koma.
- **Link Assets**: 1-2 link gambar gratis (Unsplash/Pexels) yang relevan dengan berita. Pilih berdasarkan keyword.

📰 DATA BERITA:
Judul: {article['title']}
Ringkasan: {article.get('summary', '')}
Skor: {article.get('score', 3)}
Alasan: {article.get('reason', '')}

Output: Berikan dalam format JSON **tanpa komentar tambahan**, dengan struktur:
{{
  "title": "judul alternatif",
  "subtitle": "subtitle singkat",
  "content": "teks artikel lengkap (300-400 kata)",
  "seo": "kalimat SEO",
  "tags": "tag1, tag2, tag3, ...",
  "assets": ["url_gambar1", "url_gambar2"]
}}
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "Anda adalah jurnalis berpengalaman dengan gaya santai-informatif. Output selalu JSON valid."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )

    try:
        data = json.loads(response.choices[0].message.content)
        # Ambil keyword untuk assets dari judul atau tags
        keyword = data.get('tags', '').split(',')[0].strip() if data.get('tags') else article['title'][:30]
        if not data.get('assets'):
            data['assets'] = [fetch_asset_image(keyword)]
        return data
    except:
        # Fallback jika parsing gagal
        print(f"Gagal parsing JSON untuk artikel {index}. Raw response:")
        print(response.choices[0].message.content[:200])
        return {
            "title": article['title'],
            "subtitle": "Ringkasan berita hari ini",
            "content": response.choices[0].message.content[:500],
            "seo": article['title'],
            "tags": "berita, teknologi, bisnis",
            "assets": [fetch_asset_image("technology")]
        }

def format_article_text(data, index):
    """Menggabungkan semua elemen ke dalam satu string untuk file .txt"""
    text = f"📰 **ARTIKEL #{index}**\n\n"
    text += f"**Judul:** {data['title']}\n"
    text += f"**Subtitle:** {data['subtitle']}\n\n"
    text += f"**Konten:**\n{data['content']}\n\n"
    text += f"**Kalimat SEO:** {data['seo']}\n"
    text += f"**Tags:** {data['tags']}\n"
    text += f"**Assets (Gambar):**\n"
    for asset in data.get('assets', []):
        text += f"- {asset}\n"
    text += "\n" + "="*60 + "\n\n"
    return text

if __name__ == "__main__":
    print("📖 Membaca top5.json...")
    top5 = load_top5()
    if not top5:
        print("Tidak ada top5.json. Jalankan curator dulu.")
        exit(0)

    # Urutkan berdasarkan skor (tertinggi ke rendah)
    top5_sorted = sorted(top5, key=lambda x: x.get('score', 0), reverse=True)

    full_output = f"The Quartr - Newsletter {get_current_date_wib()}\n\n"
    full_output += "="*50 + "\n\n"

    for idx, article in enumerate(top5_sorted, 1):
        print(f"✍️ Menulis artikel #{idx}: {article['title']}")
        data = write_full_article(article, idx)
        article_text = format_article_text(data, idx)
        full_output += article_text

    # Simpan ke file
    save_article(full_output, "Artikel.txt")
    print("✅ Artikel.txt berhasil dibuat.")

    # Kirim ke Telegram
    print("📤 Mengirim ke Telegram...")
    send_to_telegram(full_output)
    print("✅ Terkirim ke Telegram.")
