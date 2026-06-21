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

def load_style_dna(filename="Style DNA.txt"):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("⚠️ Style DNA.txt tidak ditemukan.")
        return ""

def parse_articles_txt(filename="Artikel.txt"):
    """
    Parsing Artikel.txt untuk ekstrak setiap artikel.
    Format: 📰 ARTIKEL #N ... Judul: ... Subtitle: ... [content] ... Kalimat SEO: ... Tags: ... Assets: ...
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print("⚠️ Artikel.txt tidak ditemukan.")
        return []

    articles = []
    blocks = re.split(r'📰 ARTIKEL #\d+\n+', content)
    for block in blocks[1:]:
        lines = block.strip().split('\n')
        data = {"title": "", "subtitle": "", "content": "", "seo": "", "tags": ""}
        in_content = False
        content_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('Judul: '):
                data['title'] = stripped.replace('Judul: ', '').strip()
            elif stripped.startswith('Subtitle: '):
                data['subtitle'] = stripped.replace('Subtitle: ', '').strip()
                in_content = True
            elif stripped.startswith('Kalimat SEO: '):
                data['seo'] = stripped.replace('Kalimat SEO: ', '').strip()
                in_content = False
            elif stripped.startswith('Tags: '):
                data['tags'] = stripped.replace('Tags: ', '').strip()
            elif stripped.startswith('Assets') or stripped.startswith('='):
                in_content = False
            elif in_content:
                content_lines.append(line)

        data['content'] = '\n'.join(content_lines).strip()
        if data['title'] and data['content']:
            articles.append(data)

    print(f"✅ {len(articles)} artikel ditemukan di Artikel.txt.")
    return articles

def send_to_telegram(text, caption=""):
    import subprocess
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ Token/chat ID tidak ditemukan.")
        return

    if len(text) > 4000:
        filename = "styled_articles.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(text)
        subprocess.run([
            "curl", "-s", "-X", "POST",
            f"https://api.telegram.org/bot{token}/sendDocument",
            "-F", f"chat_id={chat_id}",
            "-F", f"document=@{filename}",
            "-F", f"caption={caption or '📝 Artikel dengan Style DNA'}",
        ])
    else:
        subprocess.run([
            "curl", "-s", "-X", "POST",
            f"https://api.telegram.org/bot{token}/sendMessage",
            "-F", f"chat_id={chat_id}",
            "-F", f"text={text}",
            "-F", "parse_mode=Markdown",
        ])

def format_article(data, index):
    text = f"📰 ARTIKEL #{index}\n\n"
    text += f"**Judul:** {data.get('title', '')}\n"
    text += f"**Subtitle:** {data.get('subtitle', '')}\n\n"
    text += f"{data.get('content', '')}\n\n"
    text += f"🔍 **SEO:** {data.get('seo', '')}\n"
    text += f"🏷️ **Tags:** {data.get('tags', '')}\n\n"
    text += "="*50 + "\n\n"
    return text

# ================================
# WRITER CORE (REWRITE DENGAN STYLE DNA)
# ================================

def rewrite_with_style(article, index, style_dna):
    """
    Menulis ulang draft artikel dengan gaya berdasarkan Style DNA.
    """
    prompt = f"""Anda adalah editor untuk newsletter "The Quartr". 
Tulislah ulang draft artikel di bawah ini dengan **MENIRU GAYA PENULISAN** yang sudah ditentukan.

📌 **ACUAN GAYA (WAJIB DITIRU):**
{style_dna}

📌 **DRAFT MENTAH YANG HARUS DITULIS ULANG:**
Judul: {article.get('title', '')}
Subtitle: {article.get('subtitle', '')}
Konten: {article.get('content', '')}
SEO: {article.get('seo', '')}
Tags: {article.get('tags', '')}

ATURAN GAYA (IKUTI):
1. Pembuka: Jangan pakai "Bayangkan". Pakai salah satu: analogi, ironi, atau fakta mengejutkan.
2. Transisi: Pakai kata sambung alami (Tapi, Sementara itu, Yang jadi masalah).
3. Kalimat pendek: Sisipkan 1-2 kalimat pendek (3-5 kata) per paragraf.
4. Humor: Tambahkan 1 observasi ringan/sindiran halus di setiap artikel.
5. Penutup: Jangan pakai "Pertanyaannya sekarang". Akhiri dengan prediksi atau implikasi.

LARANGAN:
- Jangan pakai: berdasarkan, sejalan dengan, dalam rangka, guna, oleh karena itu, adapun.
- Jangan pakai: dampaknya langsung terasa, ke depannya, tidak hanya... tapi juga.

DRAFT MENTAH:
Judul: {article.get('title', '')}
Subtitle: {article.get('subtitle', '')}
Konten: {article.get('content', '')}

Output harus berupa JSON dengan field: 
{{ "title": "judul baru", "subtitle": "subtitle baru", "content": "teks artikel", "seo": "kalimat SEO", "tags": "tag1, tag2" }}
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Anda adalah editor yang meniru gaya Morning Brew versi Indonesia. Output JSON valid."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
    except Exception as e:
        print(f"❌ API error untuk artikel {index}: {e}")
        return article  # Kembalikan draft asli jika error

    raw = response.choices[0].message.content
    print(f"📝 Raw response artikel #{index}: {raw[:200]}...")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except:
                data = None
        else:
            data = None

    if data is None:
        print(f"❌ Gagal parsing JSON artikel {index}. Gunakan draft asli.")
        return article

    # Gabungkan hasil rewrite dengan draft asli (jika ada field kosong)
    for key in ['title', 'subtitle', 'content', 'seo', 'tags']:
        if key not in data or not data[key]:
            data[key] = article.get(key, '')

    return data

# ================================
# MAIN
# ================================

def main():
    print("📖 Membaca Artikel.txt...")
    drafts = parse_articles_txt("Artikel.txt")
    if not drafts:
        print("❌ Tidak ada artikel di Artikel.txt. Keluar.")
        return

    style_dna = load_style_dna()
    if not style_dna:
        print("⚠️ Style DNA tidak ditemukan. Gunakan draft asli.")
        # Kirim draft asli ke Telegram
        output = "📰 The Quartr — Draft Artikel (tanpa Style DNA)\n\n"
        for idx, art in enumerate(drafts, 1):
            output += format_article(art, idx)
        send_to_telegram(output, caption="📝 Draft mentah (Style DNA tidak ditemukan)")
        return

    print("✍️ Menulis ulang artikel dengan Style DNA...")
    polished = []
    for idx, article in enumerate(drafts, 1):
        print(f"  Memproses artikel #{idx}: {article.get('title', '')[:50]}...")
        result = rewrite_with_style(article, idx, style_dna)
        polished.append(result)

    output = "📰 The Quartr — Artikel dengan Style DNA\n\n"
    for idx, data in enumerate(polished, 1):
        output += format_article(data, idx)

    print("📤 Mengirim ke Telegram...")
    send_to_telegram(output, caption="📝 Artikel dengan Style DNA The Quartr")

    with open("styled_articles.txt", "w", encoding="utf-8") as f:
        f.write(output)

    print("✅ Selesai. File: styled_articles.txt")

if __name__ == "__main__":
    main()
