import json
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

def load_articles(filename="news.json"):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_top5(articles, filename="top5.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

def curate_top5(all_articles):
    # Siapkan daftar artikel untuk prompt (tanpa batasan)
    articles_for_prompt = []
    for idx, art in enumerate(all_articles, 1):
        summary_clean = art.get("summary", "").replace('\n', ' ').replace('\r', '')
        articles_for_prompt.append({
            "id": idx,
            "title": art["title"],
            "summary": summary_clean[:500],  # batasi agar token tidak overload
            "link": art.get("link", ""),
            "published": art.get("published", ""),
            "source": art.get("source", "").split('|')[0].strip()  # tambahkan sumber
        })
    
    # ====== PROMPT BARU DENGAN ATURAN VARIASI ======
    prompt = """Anda adalah kurator berita bisnis dan teknologi startup yang sangat berpengalaman. 
Tugas: pilih 5 berita yang paling penting, berdampak, dan ramai diperbincangkan, tetapi dengan VARIASI yang tinggi.

ATURAN VARIASI (WAJIB):
1. **Minimal harus mencakup 4 sektor berbeda** dari daftar sektor dibawah ini
2. **Maksimal 2 berita dari sektor yang sama** (misal: jangan 3 tentang AI atau 3 tentang SpaceX).
3. **Maksimal 1 berita dari sumber yang sama** (jangan pilih 2 dari TechCrunch, 2 dari Forbes, dll.).
4. **Prioritaskan berita yang dipublikasikan dalam 24 jam terakhir** (lihat field "published").
5. **Hindari mengulang topik yang sudah muncul di 2 hari terakhir** (gunakan kebijaksanaan Anda).

Daftar sektor:
- **Pendanaan & IPO** (funding rounds, IPO, valuasi, akuisisi)
- **Regulasi & Kebijakan** (kebijakan pemerintah, pajak, larangan)
- **Startup & Inovasi** (produk baru, teknologi disruptif, founder)
- **Pasar Modal & Ekonomi Makro** (saham, inflasi, suku bunga, pasar global)
- **Korporasi & M&A** (akuisisi besar, merger, ekspansi perusahaan)
- **Teknologi AI & Digital** (AI, cloud, cybersecurity, digital transformation)

Skor (1-5) tetap digunakan, tetapi pertimbangkan variasi sebagai faktor penambah nilai.

Berikan penilaian (score) untuk setiap berita yang dipilih dengan skala 1-5, di mana:
- 5 = sangat penting, berdampak besar, dan sangat ramai (misal: IPO besar, akuisisi raksasa, perubahan regulasi global)
- 4 = penting, berdampak signifikan, cukup ramai (misal: pendanaan besar, peluncuran produk disruptif)
- 3 = cukup penting, berdampak sedang, ramai di kalangan tertentu
- 2 = kurang penting, dampak terbatas, tidak terlalu ramai
- 1 = tidak penting (tidak akan dipilih)

Kriteria penilaian (selain variasi):
- Dampak terhadap pasar modal, bisnis, startup, regulasi, atau industri teknologi secara luas.
- Jumlah nilai transaksi (pendanaan, akuisisi, IPO) jika ada.
- Relevansi untuk eksekutif, investor, dan pelaku startup di Asia Tenggara (prioritaskan yang relevan).
- Kebaruan dan potensi tren jangka panjang.

Output: Berikan dalam format JSON **tanpa komentar tambahan**, berupa array of objects dengan field:
{
  "title": (string, judul asli),
  "summary": (string, ringkasan asli),
  "link": (string, URL asli),
  "published": (string, tanggal publikasi asli),
  "score": (integer, 1-5),
  "reason": (string singkat, alasan mengapa berita ini penting dan skor tersebut, serta sebutkan sektornya)
}

Pilih 5 berita. Jika ada berita dengan skor di bawah 3, pertimbangkan untuk tidak memasukkannya, tetapi tetap usahakan 5 berita terbaik dengan variasi tinggi.

Berikut daftar berita (format: ID | Sumber | Tanggal | Title | Summary):
"""
    for item in articles_for_prompt:
        prompt += f"\n{item['id']} | {item.get('source', 'Unknown')} | {item['published']} | {item['title']} | {item['summary']}..."

    # ====== AKHIR PROMPT ======

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "Anda adalah kurator berita yang sangat selektif dan berpengalaman 20 tahun. Utamakan variasi sektor dan sumber, serta kebaruan."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    result_text = response.choices[0].message.content
    try:
        data = json.loads(result_text)
        if isinstance(data, dict):
            if "berita" in data:
                selected = data["berita"]
            elif "articles" in data:
                selected = data["articles"]
            else:
                selected = list(data.values())[0] if data else []
        elif isinstance(data, list):
            selected = data
        else:
            selected = []
    except:
        print("Gagal parsing JSON dari DeepSeek. Raw response:")
        print(result_text)
        selected = []
    
    # Gabungkan dengan data asli
    id_to_original = {i+1: all_articles[i] for i in range(len(all_articles))}
    top5_articles = []
    for item in selected:
        found = None
        for orig in all_articles:
            if orig["title"] == item.get("title") or orig.get("link") == item.get("link"):
                found = orig
                break
        if found:
            article_copy = found.copy()
            article_copy["score"] = item.get("score", 3)
            article_copy["reason"] = item.get("reason", "")
            top5_articles.append(article_copy)
    
    # Fallback jika kurang dari 5
    if len(top5_articles) < 5 and len(all_articles) >= 5:
        selected_titles = [a["title"] for a in top5_articles]
        for orig in all_articles:
            if orig["title"] not in selected_titles and len(top5_articles) < 5:
                article_copy = orig.copy()
                article_copy["score"] = 3
                article_copy["reason"] = "Fallback: berita ini cukup penting."
                top5_articles.append(article_copy)
    
    return top5_articles

if __name__ == "__main__":
    print("📖 Membaca news.json...")
    articles = load_articles()
    print(f"Total artikel: {len(articles)}")
    if not articles:
        print("Tidak ada artikel. Keluar.")
        exit(0)
    
    print("🤖 Meminta DeepSeek memilih 5 berita terpenting dengan skor 1-5...")
    top5 = curate_top5(articles)
    print(f"✅ Terpilih {len(top5)} berita.")
    save_top5(top5)
    print("💾 Disimpan ke top5.json")
    
    for i, art in enumerate(top5, 1):
        print(f"{i}. {art['title']} - Score: {art.get('score', 'N/A')} - {art.get('reason', '')}")
