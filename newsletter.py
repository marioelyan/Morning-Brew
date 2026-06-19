import json
import os
import re
from openai import OpenAI
from datetime import datetime, timedelta, timezone

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

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
            # Ambil paragraf pertama sebagai ringkasan (untuk bullet)
            summary = content_text.split('\n\n')[0] if content_text else ""
            if len(summary) > 200:
                summary = summary[:200] + "..."
            articles.append({
                'title': title,
                'subtitle': subtitle,
                'content': content_text,
                'summary': summary
            })

    return articles

def generate_hook_and_bullets(articles):
    """
    Menghasilkan hook yang NATURAL (bukan ringkasan berita) + bullet list preview.
    """
    # Ambil judul untuk konteks
    titles = [art.get('title', '') for art in articles[:5]]

    prompt = f"""Kamu adalah mantan penulis newsletter "Morning Brew". Berpengalaman 20 tahun dalam penulisan newsletter maupun artikel berita.
Buatlah dua bagian untuk pembuka newsletter hari ini:

**Bagian 1: Paragraf Hook (Pembuka)**
- Tujuannya: MENARIK PERHATIAN, bukan merangkum berita.
- Bisa berupa: Pertanyaan reflektif, observasi ringan, sapaan hangat, atau fakta menarik yang tidak disebutkan di berita.
- JANGAN menyebutkan judul atau detail berita di hook — itu tugas bullet list di bawah.
- 1 paragraf (40-60 kata).
- Gaya: santai, personal, seperti berbicara dengan teman yang pintar.

**Bagian 2: Bullet List Preview (5 berita)**
- 5 bullet point, masing-masing 1 kalimat singkat (10-15 kata).
- Format: "- Ringkasan singkat"
- Langsung ke inti, tanpa basa-basi.

📰 Judul berita hari ini (hanya untuk konteks, JANGAN disebut di hook):
{chr(10).join(f'- {title}' for title in titles)}

Output: Berikan dalam format JSON **tanpa komentar tambahan**:
{{
  "hook": "teks paragraf hook (tanpa detail berita)",
  "bullets": [
    "- ringkasan berita 1",
    "- ringkasan berita 2",
    "- ringkasan berita 3",
    "- ringkasan berita 4",
    "- ringkasan berita 5"
  ]
}}
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "Anda penulis newsletter dengan gaya personal dan hangat. Hook harus natural, bukan ringkasan berita."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )

    try:
        data = json.loads(response.choices[0].message.content)
        hook = data.get('hook', '')
        bullets = data.get('bullets', [])
        while len(bullets) < 5:
            bullets.append(f"- {articles[len(bullets)].get('title', 'Berita')[:50]}...")
        return hook, bullets
    except Exception as e:
        print(f"Gagal parsing hook: {e}")
        # Fallback natural
        fallback_hooks = [
            "Pagi, Quartrian! Semoga hari ini membawa ide-ide segar untukmu.",
            "Selamat pagi! Yuk kita sambut hari dengan wawasan baru.",
            "Halo, Quartrian! Siap untuk lima berita terbaik hari ini?",
            "Morning! Semoga kopi dan berita hari ini sama-sama hangat."
        ]
        import random
        hook = random.choice(fallback_hooks)
        bullets = [f"- {art.get('title', 'Berita')[:60]}..." for art in articles[:5]]
        return hook, bullets

def generate_quarter_time(articles):
    prompt = f"""Kamu adalah mantan penulis newsletter "Morning Brew". Berpengalaman 20 tahun dalam penulisan newsletter maupun artikel berita.
Buatlah konten untuk segmen "Quarter Time" — bagian ringan yang memberikan nilai tambah.

📌 Gaya penulisan: 
- Santai tapi profesional, seperti berbicara dengan teman yang cerdas.
- 1-2 paragraf (80-120 kata), isinya bisa: rekomendasi buku/youtube, kutipan inspiratif, analisis tren, atau fakta menarik.

Berita hari ini:
"""
    for art in articles[:5]:
        prompt += f"\n- {art.get('title', '')}"
    prompt += "\n\nOutput: Hanya teks Quarter Time, tanpa embel-embel."

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "Anda penulis newsletter dengan gaya santai-profesional."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def generate_quiz(articles):
    topics = []
    for art in articles[:5]:
        title = art.get('title', '')
        for keyword in ['AI', 'chip', 'SpaceX', 'Amazon', 'Nvidia', 'startup', 'investasi', 'robot', 'coding', 'regulasi']:
            if keyword.lower() in title.lower():
                topics.append(keyword)
                break
    topic = topics[0] if topics else "teknologi"

    prompt = f"""Kamu adalah mantan penulis newsletter "Morning Brew". Berpengalaman 20 tahun dalam penulisan newsletter maupun artikel berita.
Buatlah mini kuis dengan 1 pertanyaan pilihan ganda tentang **pengetahuan umum** yang relevan dengan tema berita hari ini.

📌 Aturan:
- Pertanyaan tentang pengetahuan umum (sejarah teknologi, ekonomi, tokoh penting, fakta sains, dll.)
- Jangan buat pertanyaan yang jawabannya ada di berita hari ini.
- 4 opsi (A, B, C, D), satu jawaban benar.

Format output JSON:
{{
  "question": "teks pertanyaan",
  "options": ["A. opsi 1", "B. opsi 2", "C. opsi 3", "D. opsi 4"],
  "answer": "A"
}}

Tema hari ini (dari judul berita):
"""
    for art in articles[:5]:
        prompt += f"\n- {art.get('title', '')}"
    prompt += "\n\nOutput: JSON valid, tanpa komentar tambahan."

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "Anda pembuat kuis dengan wawasan luas."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )
    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {
            "question": "Siapa pendiri SpaceX?",
            "options": ["A. Jeff Bezos", "B. Elon Musk", "C. Richard Branson", "D. Bill Gates"],
            "answer": "B"
        }

def generate_subject(articles):
    prompt = f"""Kamu adalah mantan penulis newsletter "Morning Brew". Berpengalaman 20 tahun dalam penulisan newsletter maupun artikel berita.
Buatlah subjek email (1 kalimat, 10-15 kata) yang menarik dan profesional.

📌 Gaya:
- Menarik, membuat penasaran, tapi tidak clickbait.
- Mencerminkan dunia hari ini.
- Santai tapi profesional.

Berita hari ini:
"""
    for art in articles[:3]:
        prompt += f"\n- {art.get('title', '')}"
    prompt += "\n\nOutput: Hanya teks subjek, tanpa tanda kutip atau embel-embel."

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "Anda ahli menulis subjek email yang profesional."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def format_newsletter(articles, hook, bullets, quarter_time, quiz_data, subject, date):
    text = f"📰 **{subject}**\n\n"
    text += f"*The Quartr — {date}*\n\n"
    text += "──────────────────────────────────────────────────\n\n"

    # Hook (tanpa detail berita)
    text += "## 🎯 The Hook\n"
    text += f"{hook}\n\n"
    text += "📌 Apa yang terjadi hari ini:\n"
    for bullet in bullets:
        text += f"{bullet}\n"
    text += "\n──────────────────────────────────────────────────\n\n"

    # Core Stories
    text += "## 📌 The Core Stories\n\n"
    for idx, art in enumerate(articles[:5], 1):
        title = art.get('title', f'Berita {idx}')
        content = art.get('content', '')
        if not content:
            content = "Konten tidak tersedia."
        text += f"### {idx}. {title}\n\n"
        text += f"{content}\n\n"
    text += "──────────────────────────────────────────────────\n\n"

    # Quarter Time
    text += "## 🧠 Quarter Time\n"
    text += f"{quarter_time}\n\n"
    text += "──────────────────────────────────────────────────\n\n"

    # Gamification
    text += "## 🎮 Gamification\n"
    text += f"**Kuis Mini:**\n"
    text += f"{quiz_data.get('question', '')}\n"
    for opt in quiz_data.get('options', []):
        text += f"- {opt}\n"
    text += "\n*Jawaban akan diumumkan di Instagram Story!* 😉\n\n"
    text += "──────────────────────────────────────────────────\n\n"

    # Footer
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
                    "content": item.get("summary", ""),
                    "summary": item.get("summary", "")[:150] + "..."
                })
        except:
            print("❌ Gagal memuat data. Keluar.")
            exit(1)

    print("🤖 Menghasilkan hook natural + bullet preview...")
    hook, bullets = generate_hook_and_bullets(articles)

    print("🧠 Menghasilkan Quarter Time...")
    quarter_time = generate_quarter_time(articles)

    print("🎮 Menghasilkan kuis...")
    quiz_data = generate_quiz(articles)

    print("📧 Menghasilkan subjek email...")
    subject = generate_subject(articles)

    date = get_date_formatted()

    print("📝 Menyusun newsletter...")
    newsletter = format_newsletter(articles, hook, bullets, quarter_time, quiz_data, subject, date)

    with open("newsletter_substack.txt", "w", encoding="utf-8") as f:
        f.write(newsletter)

    print("✅ Newsletter siap di-copy ke Substack!")
    print("📄 File: newsletter_substack.txt")
    print(f"📧 Subjek: {subject}")
