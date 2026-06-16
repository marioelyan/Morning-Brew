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
            "published": art.get("published", "")
        })
    
    prompt = """Anda adalah kurator berita bisnis dan teknologi startup yang sangat berpengalaman. 
Tugas: pilih 5 berita yang paling penting, berdampak, dan ramai diperbincangkan dari daftar di bawah ini.

Berikan penilaian (score) untuk setiap berita yang dipilih dengan skala 1-5, di mana:
- 5 = sangat penting, berdampak besar, dan sangat ramai (misal: IPO besar, akuisisi raksasa, perubahan regulasi global)
- 4 = penting, berdampak signifikan, cukup ramai (misal: pendanaan besar, peluncuran produk disruptif)
- 3 = cukup penting, berdampak sedang, ramai di kalangan tertentu
- 2 = kurang penting, dampak terbatas, tidak terlalu ramai
- 1 = tidak penting (tidak akan dipilih)

Kriteria penilaian:
- Dampak terhadap pasar modal, startup, atau industri teknologi secara luas.
- Jumlah nilai transaksi (pendanaan, akuisisi, IPO) jika ada.
- Relevansi untuk eksekutif, investor, dan pelaku startup di Asia Tenggara (prioritaskan yang relevan).
- Kebaruan dan potensi tren jangka panjang.
- Seberapa banyak dibicarakan di media dan komunitas.

Output: Berikan dalam format JSON **tanpa komentar tambahan**, berupa array of objects dengan field:
{
  "title": (string, judul asli),
  "summary": (string, ringkasan asli),
  "link": (string, URL asli),
  "published": (string, tanggal publikasi asli),
  "score": (integer, 1-5),
  "reason": (string singkat, alasan mengapa berita ini penting dan skor tersebut)
}

Pilih 5 berita. Jika ada berita dengan skor di bawah 3, pertimbangkan untuk tidak memasukkannya, tetapi tetap usahakan 5 berita terbaik.

Berikut daftar berita (format: ID | Title | Summary):
"""
    for item in articles_for_prompt:
        prompt += f"\n{item['id']} | {item['title']} | {item['summary']}..."

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "Anda adalah kurator berita yang sangat selektif dan objektif. Berikan output selalu dalam format JSON yang valid."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    result_text = response.choices[0].message.content
    try:
        data = json.loads(result_text)
        if isinstance(data, dict):
            # Coba cari array di dalam dict
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
    
    # Gabungkan dengan data asli (untuk memastikan semua field ada)
    id_to_original = {i+1: all_articles[i] for i in range(len(all_articles))}
    top5_articles = []
    for item in selected:
        found = None
        # Coba cari berdasarkan title atau link
        for orig in all_articles:
            if orig["title"] == item.get("title") or orig.get("link") == item.get("link"):
                found = orig
                break
        if found:
            article_copy = found.copy()
            article_copy["score"] = item.get("score", 3)
            article_copy["reason"] = item.get("reason", "")
            top5_articles.append(article_copy)
    
    # Jika kurang dari 5, tambahkan sisa dengan skor 3 (fallback)
    if len(top5_articles) < 5 and len(all_articles) >= 5:
        # Ambil artikel yang belum terpilih (berdasarkan title)
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
