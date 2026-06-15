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
    # Tanpa batasan: semua artikel dan summary penuh
    articles_for_prompt = []
    for idx, art in enumerate(all_articles, 1):
        articles_for_prompt.append({
            "id": idx,
            "title": art["title"],
            "summary": art.get("summary", "")  # tanpa potongan
        })
    
    prompt = """Anda adalah kurator berita bisnis dan teknologi startup. 
Berikut adalah daftar berita dari berbagai sumber (TechCrunch, Fortune, Entrepreneur, Forbes, Crunchbase).

Tugas: pilih 5 berita yang paling penting, relevan, dan berdampak untuk eksekutif dan investor startup.

Kriteria:
- Inovasi teknologi disruptif
- Pendanaan atau valuasi startup
- Akuisisi atau IPO
- Perubahan regulasi signifikan
- Tren pasar yang muncul

Berikan output dalam format JSON **tanpa komentar tambahan**, seperti:
[
  {
    "id": 1,
    "title": "...",
    "reason": "alasan singkat",
    "original_index": (nomor urut asli dari daftar di bawah)
  },
  ...
]

Berikut daftar berita (format: id | title | summary):
"""
    for item in articles_for_prompt:
        # Ganti newline agar tidak merusak format
        summary_clean = item["summary"].replace('\n', ' ').replace('\r', '')
        prompt += f"\n{item['id']} | {item['title']} | {summary_clean}"

    # Panggil DeepSeek
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "Anda adalah kurator berita yang sangat selektif."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    result_text = response.choices[0].message.content
    try:
        selected = json.loads(result_text)
    except:
        print("Gagal parsing JSON dari DeepSeek. Raw response:")
        print(result_text)
        selected = []
    
    # Peta id asli ke artikel lengkap
    id_to_original = {i+1: all_articles[i] for i in range(len(all_articles))}
    top5_articles = []
    for item in selected:
        orig_id = item.get("original_index") or item.get("id")
        if orig_id and orig_id in id_to_original:
            article_copy = id_to_original[orig_id].copy()
            article_copy["curation_reason"] = item.get("reason", "")
            top5_articles.append(article_copy)
    
    return top5_articles

if __name__ == "__main__":
    print("📖 Membaca news.json...")
    articles = load_articles()
    print(f"Total artikel: {len(articles)}")
    if not articles:
        print("Tidak ada artikel. Keluar.")
        exit(0)
    
    print("🤖 Meminta DeepSeek memilih 5 berita terpenting (tanpa batasan teks)...")
    top5 = curate_top5(articles)
    print(f"✅ Terpilih {len(top5)} berita.")
    save_top5(top5)
    print("💾 Disimpan ke top5.json")
    
    for i, art in enumerate(top5, 1):
        print(f"{i}. {art['title']} - {art.get('curation_reason', '')}")
