# SOP The Quartr - Edisi Selasa/Kamis

## H-1 (Senin/Rabu malam)
1. Tidak ada tindakan. Pastikan cron-job.org aktif.

## H+0 (Selasa/Kamis pagi)
1. 05:00 WIB: Cek Telegram, pastikan `full-issue-draft.zip` masuk.
2. 05:05 - 05:15: Buka `template_newsletter.txt`.
3. Editing:
   - [ ] Isi Hook (1 paragraf)
   - [ ] Isi Quarter Time (rekomendasi)
   - [ ] Isi Kuis
   - [ ] Ubah 1-2 kalimat di setiap artikel agar lebih "nendang".
4. Upload gambar header (Unsplash).
5. Copy-paste ke Substack, preview, publish.
6. Backup: Simpan final edit ke Google Docs (atau Supabase nanti).

## Jika Error (Workflow gagal)
1. Cek log GitHub Actions.
2. Jika error di writer.py, jalankan ulang workflow manual (workflow_dispatch).
3. Jika tetap error, jalankan `python writer.py` lokal (jika ada akses).