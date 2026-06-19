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
    for block in blocks[1:]:  # skip header
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

def get_visual_suggestions(articles):
    """
    Memberikan saran visual untuk setiap segmen berdasarkan keyword dari judul berita.
    """
    # Kumpulkan keyword dari judul
    all_keywords = []
    for art in articles[:5]:
        words = art.get('title', '').split()
        # Ambil kata penting (minimal 3 huruf)
        keywords = [w for w in words if len(w) > 3]
        all_keywords.extend(keywords[:2])
    
    # Ambil keyword paling umum
    keyword_counts = {}
    for kw in all_keywords:
        kw_lower = kw.lower()
        keyword_counts[kw_lower] = keyword_counts.get(kw_lower, 0) + 1
    
    top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
    main_topic = top_keywords[0][0] if top_keywords else "technology"
    
    # Map keyword ke saran visual
    visual_map = {
        "ai": "Gambar AI/robot dari Unsplash (keyword: 'artificial intelligence')",
        "space": "Gambar roket/astronot dari Unsplash (keyword: 'space' atau 'rocket')",
        "startup": "Gambar kantor startup atau tim sedang meeting (keyword: 'startup office')",
        "investasi": "Gambar grafik saham atau uang (keyword: 'stock market' atau 'finance')",
        "regulasi": "Gambar gedung pemerintah atau ruang sidang (keyword: 'government' atau 'court')",
        "chip": "Gambar mikrochip atau papan sirkuit (keyword: 'microchip' atau 'processor')",
        "ipo": "Gambar lonceng bursa atau grafik naik (keyword: 'ipo' atau 'stock exchange')",
        "akuisisi": "Gambar jabat tangan atau kontrak (keyword: 'handshake' atau 'merger')",
        "teknologi": "Gambar abstrak teknologi (keyword: 'technology' atau 'digital')",
        "bisnis": "Gambar gedung perkantoran atau ruang rapat (keyword: 'business' atau 'office')",
    }
    
    # Cari saran berdasarkan keyword utama
    suggestion = None
    for kw, img in visual_map.items():
        if kw in main_topic:
            suggestion = img
            break
    
    if not suggestion:
        suggestion = "Gambar umum teknologi/bisnis dari Unsplash (keyword: 'technology business')"
    
    return {
        "hero_image": suggestion,
        "main_topic": main_topic
    }

def build_newsletter_template(articles, date):
    """
    Membangun template newsletter Substack dengan placeholder untuk diedit,
    dilengkapi instruksi visual.
    """
    visual = get_visual_suggestions(articles)
    
    # ============================================================
    # TEMPLATE UTAMA
    # ============================================================
    text = "="*60 + "\n"
    text += "📌 TEMPLATE NEWSLETTER THE QUARTR — SUBSTACK\n"
    text += "="*60 + "\n\n"
    text += "📝 INSTRUKSI:\n"
    text += "1. Isi semua bagian yang diawali dan diakhiri dengan {{...}}\n"
    text += "2. Ikuti saran visual di bawah ini untuk gambar/embed\n"
    text += "3. Setelah selesai, copy-paste seluruh teks ke editor Substack\n"
    text += "4. Hapus baris instruksi ini sebelum publish\n"
    text += "-"*60 + "\n\n"

    # HEADER
    text += "📰 **{{ISI JUDUL MENARIK DI SINI (10-15 KATA)}}**\n\n"
    text += f"*The Quartr — {date}*\n\n"
    
    # ============================================================
    # VISUAL SUGGESTION: HERO IMAGE
    # ============================================================
    text += "🖼️ **SUGGESTION HERO IMAGE:**\n"
    text += f"   {visual['hero_image']}\n"
    text += "   Upload gambar 1200x628 px di bagian 'Add Cover' di Substack.\n\n"
    text += "──────────────────────────────────────────────────\n\n"

    # ============================================================
    # SEGMEN 1: THE HOOK
    # ============================================================
    text += "## 🎯 The Hook\n"
    text += "{{TULIS PARAGRAF PEMBUKA YANG MENARIK (40-60 KATA)}}\n"
    text += "\n💡 **Tips Visual:**\n"
    text += "   - Bisa tambahkan embed tweet atau postingan X yang relevan di bawah hook.\n"
    text += "   - Tempelkan link X/Instagram di baris kosong untuk otomatis embed.\n\n"
    
    text += "📌 **In today's newsletter:**\n"
    for idx, art in enumerate(articles[:5], 1):
        title = art.get('title', f'Berita {idx}')
        text += f"- {{RINGKASAN SINGKAT BERITA {idx}: {title[:50]}...}}\n"
    text += "\n──────────────────────────────────────────────────\n\n"

    # ============================================================
    # SEGMEN 2: THE CORE STORIES
    # ============================================================
    text += "## 📌 The Core Stories\n\n"
    text += "💡 **Tips Visual:**\n"
    text += "   - Setiap berita bisa ditambahkan gambar inline (upload di sela-sela teks).\n"
    text += "   - Gunakan Pull Quote (ikon kutip) untuk 1 kalimat mengejutkan per artikel.\n"
    text += "   - Jika ada data angka (grafik), pertimbangkan embed tabel atau gambar.\n\n"
    
    for idx, art in enumerate(articles[:5], 1):
        title = art.get('title', f'Berita {idx}')
        content = art.get('content', '')
        if not content:
            content = "Konten tidak tersedia."
        
        text += f"### {idx}. {title}\n\n"
        text += f"{content}\n\n"
        
        # Saran Pull Quote
        sentences = content.split('. ')
        if sentences:
            # Ambil kalimat pertama sebagai pull quote
            first_sentence = sentences[0].strip()
            if len(first_sentence) > 30:
                text += f"📌 **PULL QUOTE SUGGESTION:**\n"
                text += f"   > \"{first_sentence}\"\n"
                text += f"   (Gunakan format Quote di Substack untuk menonjolkan kalimat ini)\n\n"
        text += "---\n\n"
    
    text += "──────────────────────────────────────────────────\n\n"

    # ============================================================
    # SEGMEN 3: QUARTER TIME
    # ============================================================
    text += "## 🧠 Quarter Time\n"
    text += "{{TULIS REKOMENDASI BUKU/PODCAST ATAU WAWASAN DI SINI (80-120 KATA)}}\n"
    text += "\n💡 **Tips Visual:**\n"
    text += "   - Jika merekomendasikan podcast, tempelkan link Spotify/Anchor untuk embed audio.\n"
    text += "   - Jika merekomendasikan buku, upload gambar sampul buku (dari Google Images).\n"
    text += "   - Bisa juga tambahkan video YouTube pendek (3-5 menit) yang relevan.\n\n"
    text += "──────────────────────────────────────────────────\n\n"

    # ============================================================
    # SEGMEN 4: GAMIFICATION
    # ============================================================
    text += "## 🎮 Gamification\n"
    text += "**Kuis Mini:**\n"
    text += "{{TULIS PERTANYAAN PILIHAN GANDA DI SINI}}\n"
    text += "- A. {{OPSI A}}\n"
    text += "- B. {{OPSI B}}\n"
    text += "- C. {{OPSI C}}\n"
    text += "- D. {{OPSI D}}\n"
    text += "\n💡 **Tips Visual:**\n"
    text += "   - Jika polling interaktif, buat tombol link ke X/LinkedIn atau Google Forms.\n"
    text += "   - Atau buat tabel sederhana untuk menjawab di kolom komentar Substack.\n"
    text += "   - Jawaban akan diumumkan di edisi besok! 😉\n\n"
    text += "──────────────────────────────────────────────────\n\n"

    # ============================================================
    # FOOTER
    # ============================================================
    text += "📬 **Ikuti The Quartr setiap hari**\n"
    text += "Dapatkan 5 berita bisnis & teknologi terbaik setiap pagi.\n"
    text += "🔗 [Subscribe di Substack](link-substack) | [Telegram](link-telegram)\n\n"
    text += "💬 Ada masukan? Balas email ini — saya selalu senang ngobrol.\n"
    text += "──────────────────────────────────────────────────\n\n"
    text += "📌 **Footer Visual:**\n"
    text += "   - Tambahkan tombol (CTA Button) untuk 'Subscribe' dan 'Telegram'.\n"
    text += "   - Bisa tambahkan logo kecil partner atau testimoni (jika ada).\n"

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

    print("🏗️ Membangun template newsletter dengan instruksi visual...")
    template = build_newsletter_template(articles, date)

    with open("template_newsletter.txt", "w", encoding="utf-8") as f:
        f.write(template)

    print("✅ Template newsletter siap diedit!")
    print("📄 File: template_newsletter.txt")
    print("📌 Isi bagian {{...}} dengan tulisanmu, ikuti saran visual, lalu copy-paste ke Substack.")
