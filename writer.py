import json
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

def load_top5(filename="top5.json"):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def write_article(article):
    """Generate artikel dengan gaya santai, informatif, dan mudah dipahami."""
    prompt = f"""Anda adalah penulis berita teknologi dan bisnis yang handal. Tulislah artikel pendek (200-250 kata) berdasarkan berita berikut.

Judul: {article['title']}
Ringkasan: {article.get('summary', '')}
Alasan penting: {article.get('reason', '')}  (jika ada)

Gaya penulisan:
- Gunakan bahasa Indonesia yang baik, tetapi santai dan tidak kaku.
- Hindari istilah teknis yang berlebihan. Jika terpaksa, jelaskan dengan singkat.
- Tulislah seperti kamu sedang bercerita kepada teman yang cerdas tapi bukan ahli di bidang itu.
- Buat paragraf pembuka yang menarik, lalu jelaskan inti berita, dan akhiri dengan kesimpulan atau dampaknya.
- Jangan gunakan subjudul, bullet points, atau markdown. Hanya paragraf berkesinambungan.
- Jangan terlalu formal (seperti surat resmi), tapi juga jangan terlalu casual (seperti chat). Cari tengah-tengah: sopan, akrab, dan jelas.
- Panjang: 200-250 kata.

Judul alternatif:
- Harus menarik, menggugah rasa penasaran, tapi tidak berlebihan (bukan clickbait).
- Dilarang menggunakan emoticon, emoji, atau simbol aneh (seperti !!!, ???, dll).
- Gunakan bahasa Indonesia yang natural dan tetap profesional.
- Panjang judul: maksimal 10 kata.

Output hanya teks artikel, tanpa embel-embel seperti "Tentu, ini artikelnya" atau judul ulang.
"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "Anda adalah penulis berita dengan gaya santai, informatif, dan mudah dicerna oleh pembaca umum."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.6,  # sedikit kreatif, tapi tetap fokus
        max_tokens=600
    )
    return response.choices[0].message.content

def send_to_telegram(article_text, title):
    import subprocess
    caption = f"📝 *{title}*\n\n{article_text}"
    if len(caption) > 4096:
        caption = caption[:4093] + "..."
    subprocess.run([
        "curl", "-s", "-X", "POST",
        f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
        "-F", f"chat_id={os.environ['TELEGRAM_CHAT_ID']}",
        "-F", f"text={caption}",
        "-F", "parse_mode=Markdown"
    ])

def save_article_to_file(article_text, title, idx):
    filename = f"article_{idx}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"{title}\n\n{article_text}")
    return filename

if __name__ == "__main__":
    print("📖 Membaca top5.json...")
    top5 = load_top5()
    if not top5:
        print("Tidak ada top5.json. Jalankan curator dulu.")
        exit(0)
    
    # Urutkan berdasarkan skor (jika ada) dari yang tertinggi
    top5_sorted = sorted(top5, key=lambda x: x.get('score', 0), reverse=True)
    
    print(f"✍️ Menulis {len(top5_sorted)} artikel dengan gaya santai & informatif...")
    for idx, article in enumerate(top5_sorted, 1):
        print(f"  [{idx}/{len(top5_sorted)}] {article['title']}")
        text = write_article(article)
        send_to_telegram(text, article['title'])
        print(f"    ✅ Terkirim ke Telegram")
        save_article_to_file(text, article['title'], idx)
    
    print("✅ Semua artikel selesai.")
