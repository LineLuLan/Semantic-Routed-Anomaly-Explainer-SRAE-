# SRAE — Hướng dẫn chạy trên máy local

> Bản tóm tắt copy-paste để chạy SRAE từ đầu trên Windows 10/11.
> Phiên bản hiện tại: **v0.2** · 29 tests passing.

---

## 1. Yêu cầu cài sẵn

| Cần có | Phiên bản | Ghi chú |
|---|---|---|
| Python | 3.13 (3.11+ cũng OK) | thêm vào PATH khi cài |
| Node.js | 20 LTS trở lên | cho Next.js dashboard |
| PostgreSQL | 18 (15+ đều được) | cài local, **không** cần Docker |
| Git | bất kỳ | để clone repo |
| Groq API key | miễn phí tại https://console.groq.com/keys | tuỳ chọn — không có key vẫn chạy được ở chế độ mock |

> **Không cần pgvector.** Phase 3 đã pivot sang ChromaDB (file-based), nên Postgres chỉ cần cài bản mặc định.

---

## 2. Clone & tạo virtualenv

```bash
git clone https://github.com/LineLuLan/Semantic-Routed-Anomaly-Explainer-SRAE-.git
cd Semantic-Routed-Anomaly-Explainer-SRAE-

# Tạo venv (Windows / Git Bash)
python -m venv .venv
source .venv/Scripts/activate     # PowerShell: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Lần đầu sẽ tải `sentence-transformers` (~90 MB model `all-MiniLM-L6-v2`) — chạy 1 lần là xong, cache vào `~/.cache/huggingface/`.

---

## 3. Cấu hình `.env`

```bash
cp .env.example .env
```

Mở `.env` và sửa 2 dòng:

```dotenv
POSTGRES_URL=postgresql+psycopg2://postgres:<password>@localhost:5432/srae
GROQ_API_KEY=gsk_...        # bỏ qua nếu chỉ chạy mock LLM
```

Các biến còn lại (`GROQ_MODEL`, `EMBEDDING_MODEL`, `LOG_LEVEL`) đã có default đúng — không cần đụng.

---

## 4. Chuẩn bị Postgres

Mở `psql` (hoặc pgAdmin) bằng user `postgres`:

```sql
CREATE DATABASE srae;
```

Áp schema + seed 504 dòng dữ liệu mẫu (7 ngày × 24 giờ × 3 metric):

```bash
python -m src.db.seed
```

Lệnh này tự apply `src/db/schema.sql` rồi chèn dữ liệu giả lập có 3 anomaly đã đánh dấu (`traffic=5000`, `sales=5`, `error_rate=12.5`).

---

## 5. Seed ChromaDB

Chạy đúng **một lần** sau khi `pip install` xong, để encode 6 business rules vào vector store:

```bash
python -m src.router.seed_chroma
```

Sẽ tạo thư mục `.chroma/` ở repo root. Đây là PersistentClient của Chroma — không cần server riêng, không cần Docker.

---

## 6. Khởi động backend (FastAPI)

```bash
python -m uvicorn src.app.api:app --reload --port 8000
```

Mở thử:
- http://localhost:8000/health → `{"status":"ok", ...}`
- http://localhost:8000/docs   → Swagger UI

---

## 7. Khởi động UI (Next.js)

Mở **terminal thứ 2**, không tắt terminal đang chạy backend:

```bash
cd webui
npm install            # lần đầu thôi
npm run dev
```

Mở http://localhost:3000 → bấm **Analyze**.

Nếu `.env` có `GROQ_API_KEY` thật → UI tự nhảy sang chế độ **LIVE GROQ**. Không có key → mặc định ở **mock LLM** (template, không gọi mạng).

---

## 8. Phím tắt trong UI

| Phím | Tác dụng |
|---|---|
| `Cmd/Ctrl + Enter` | Chạy Analyze |
| `Cmd/Ctrl + M` | Bật/tắt mock LLM (chỉ khi đã cấu hình Groq) |
| Click legend trên chart | Ẩn/hiện đường metric |

Dropdown `limit` ngay cạnh nút Analyze chọn số report tối đa (5 / 10 / 25 / 50).

---

## 9. Chạy tests

```bash
# Toàn bộ suite (cần Postgres đang chạy + đã seed)
python -m pytest -q

# Bỏ qua test cần DB
python -m pytest -q -m "not requires_db"
```

Kết quả mong đợi: **29 passed, 1 skipped**.

---

## 10. Troubleshooting nhanh

| Lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| `connection refused` khi start backend | Postgres chưa chạy hoặc `POSTGRES_URL` sai | bật service Postgres, kiểm tra password trong `.env` |
| `/analyze` trả 503 "SemanticRouter unavailable" | Chưa seed Chroma | chạy `python -m src.router.seed_chroma` |
| `400 model_decommissioned` từ Groq | `GROQ_MODEL` cũ | đặt `GROQ_MODEL=llama-3.1-8b-instant` (đã là default) |
| UI báo `Failed to fetch` | Backend chưa up hoặc port khác 8000 | kiểm tra `NEXT_PUBLIC_SRAE_API` trong `webui/.env.local` |
| `next dev` lỗi cache | Cache cũ | xoá `webui/.next/` rồi chạy lại |

---

## 11. Cấu trúc thư mục cần biết

```
src/
├── config.py         # đọc .env, settings
├── db/               # Phase 1 — schema + seed Postgres
├── ml/detector.py    # Phase 2 — IsolationForest per-metric
├── router/           # Phase 3 — ChromaDB + 6 business rules
├── llm/explainer.py  # Phase 4 — Groq + mock template + parallel calls
└── app/api.py        # Phase 5 — FastAPI /health /analyze /timeseries

webui/                # Next.js 16 dashboard
.chroma/              # vector store (file-based, gitignored)
.env                  # secrets (gitignored)
```

---

## 12. Stop everything

```bash
# Trong từng terminal: Ctrl+C để dừng uvicorn / next dev
deactivate            # thoát virtualenv
```

ChromaDB và Postgres giữ nguyên data trên đĩa — lần sau chỉ cần chạy lại bước 6 + 7.
