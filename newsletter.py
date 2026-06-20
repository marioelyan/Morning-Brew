import json
import os
import re
from datetime import datetime, timedelta, timezone

# ================================
# TOOLS
# ================================

def get_date_formatted():
    tz_wib = timezone(timedelta(hours=7))
    return datetime.now(tz_wib).strftime("%A, %d %B %Y")

def load_articles_txt(filename="Artikel.txt"):
    """
    Parsing Artikel.txt dengan format:
    📰 ARTIKEL #N
    Judul: ...
    Subtitle: ...
    [isi artikel (tanpa label Konten:)]
    Kalimat SEO: ...
    Tags: ...
    Assets: ...
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"⚠️ File {filename} tidak ditemukan.")
        return []

    articles = []
    blocks = re.split(r'📰 ARTIKEL #\d+\n+', content)
    for block in blocks[1:]:
        lines = block.strip().split('\n')
        title = ""
        subtitle = ""
        content_lines = []
        in_content = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('Judul: '):
                title = stripped.replace('Judul: ', '').strip()
            elif stripped.startswith('Subtitle: '):
                subtitle = stripped.replace('Subtitle: ', '').strip()
                in_content = True
            elif stripped.startswith('Kalimat SEO:') or stripped.startswith('Tags:') or stripped.startswith('Assets'):
                in_content = False
            elif in_content:
                content_lines.append(line)

        content_text = '\n'.join(content_lines).strip()
        if title or content_text:
            articles.append({
                'title': title,
                'subtitle': subtitle,
                'content': content_text
            })

    return articles

def build_newsletter_template(articles, date):
    """
    Membangun template newsletter Substack yang BERSIH (tanpa instruksi),
    hanya placeholder {{...}} dan struktur siap pakai.
    """
    text = ""

    # ===== HEADER =====
    text += "📰 **{{ISI JUDUL MENARIK DI SINI}}**\n\n"
    text += f"*The Quartr — {date}*\n\n"
    text += "──────────────────────────────────────────────────\n\n"

    # ===== HOOK =====
    text += "## 🎯 The Hook\n"
    text += "{{TULIS PARAGRAF PEMBUKA YANG MENARIK (40-60 KATA)}}\n\n"
    text += "📌 **In today's newsletter:**\n"
    for idx, art in enumerate(articles[:5], 1):
        title = art.get('title', f'Berita {idx}')
        text += f"- {{RINGKASAN SINGKAT BERITA {idx}: {title[:50]}...}}\n"
    text += "\n──────────────────────────────────────────────────\n\n"

    # ===== CORE STORIES =====
    text += "## 📌 The Core Stories\n\n"
    for idx, art in enumerate(articles[:5], 1):
        title = art.get('title', f'Berita {idx}')
        content = art.get('content', '')
        if not content:
            content = "Konten tidak tersedia."
        text += f"### {idx}. {title}\n\n"
        text += f"{content}\n\n"
    text += "──────────────────────────────────────────────────\n\n"

    # ===== QUARTER TIME =====
    text += "## 🧠 Quarter Time\n"
    text += "{{TULIS REKOMENDASI BUKU/PODCAST ATAU WAWASAN DI SINI (80-120 KATA)}}\n\n"
    text += "──────────────────────────────────────────────────\n\n"

    # ===== GAMIFICATION =====
    text += "## 🎮 Gamification\n"
    text += "**Kuis Mini:**\n"
    text += "{{TULIS PERTANYAAN PILIHAN GANDA DI SINI}}\n"
    text += "- A. {{OPSI A}}\n"
    text += "- B. {{OPSI B}}\n"
    text += "- C. {{OPSI C}}\n"
    text += "- D. {{OPSI D}}\n"
    text += "\n*Jawaban akan diumumkan di edisi besok!* 😉\n\n"
    text += "──────────────────────────────────────────────────\n\n"

    # ===== FOOTER =====
    text += "📬 **Ikuti The Quartr setiap hari**\n"
    text += "Dapatkan 5 berita bisnis & teknologi terbaik setiap pagi.\n"
    text += "🔗 [Subscribe di Substack](link-substack) | [Telegram](link-telegram)\n\n"
    text += "💬 Ada masukan? Balas email ini — saya selalu senang ngobrol.\n"

    return text

if __name__ == "__main__":
    print("📖 Membaca Artikel.txt untuk konten...")
    articles = load_articles_txt("Artikel.txt")
    if not articles:
        print("⚠️ Artikel.txt tidak ditemukan atau kosong. Gunakan data dari top5.json.")
        try:
            with open("top5.json", "r", encoding="utf-8") as f:
                top5 = json.load(f)
            articles = []
            for item in top5:
                articles.append({
                    "title": item.get("title", ""),
                    "subtitle": item.get("reason", ""),
                    "content": item.get("summary", "")
                })
        except Exception as e:
            print(f"❌ Gagal memuat data: {e}")
            exit(1)

    if not articles:
        print("❌ Tidak ada artikel. Keluar.")
        exit(1)

    date = get_date_formatted()

    print("🏗️ Membangun template newsletter...")
    template = build_newsletter_template(articles, date)

    with open("template_newsletter.txt", "w", encoding="utf-8") as f:
        f.write(template)

    print("✅ Template newsletter siap diedit!")
    print("📄 File: template_newsletter.txt")
    print("📌 Isi bagian {{...}} dengan tulisanmu, lalu copy-paste ke Substack.")
