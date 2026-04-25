# SYSTEM DIRECTIVE FOR CLAUDE
**Role:** You are an elite Senior Data Scientist, Lead Machine Learning Engineer, and Database Architect.
**Task:** Read this updated blueprint carefully. DO NOT start coding immediately. Your first response must be a structured plan confirming your understanding of the architecture (specifically the PostgreSQL + pgvector integration), the specific I/O of each module, and the step-by-step execution strategy. Wait for my approval before writing any code.

---

# PROJECT BLUEPRINT: SEMANTIC-ROUTED ANOMALY EXPLAINER (SRAE) - POSTGRESQL EDITION

## 1. Kiến Trúc Hấp Thụ Dữ Liệu & Lưu Trữ (PostgreSQL Foundation)
Khác với các hệ thống rời rạc, SRAE sẽ tận dụng **PostgreSQL** làm "Trái tim duy nhất" cho cả 2 luồng dữ liệu:
* **Relational Storage:** Lưu trữ dữ liệu Time-series gốc (Sales, Traffic, Logs) để Module ML có thể query trực tiếp.
* **Vector Storage (via `pgvector` extension):** Lưu trữ các "Kịch bản kinh doanh / Playbooks" dưới dạng Vector Embeddings để định tuyến bằng thuật toán Cosine Similarity.

## 2. Luồng Xử Lý & I/O Cốt Lõi (Core Pipelines)

### Module 1: ML Anomaly Detector (Phát hiện số liệu)
* **Tech:** `SQLAlchemy` (để query data), `Pandas`, `scikit-learn` (Isolation Forest).
* **Input:** Truy vấn dữ liệu từ bảng Time-series trong PostgreSQL, ép về định dạng `[timestamp, metric_name, value]`.
* **Logic:** Train model trên dữ liệu lịch sử để hiểu "mức bình thường". Quét dữ liệu mới để tìm ra điểm dị biệt.
* **Output:** JSON chứa thông tin lỗi: `{"timestamp": "2026-04-25 01:00", "metric": "traffic", "value": 5000, "status": "anomaly"}`

### Module 2: Semantic Router (Định tuyến Ngữ nghĩa)
* **Tech:** `PostgreSQL` (bật extension `pgvector`), `psycopg2` / `SQLAlchemy`, `sentence-transformers` (all-MiniLM-L6-v2).
* **Input:** Chuỗi văn bản hóa từ Module 1: *"Metric traffic reached 5000 at 01:00 AM."*
* **Logic:** Biến Input thành Vector nội bộ. Dùng phép toán tìm kiếm láng giềng gần nhất (k-NN) bằng toán tử `<=>` (Cosine Distance) của `pgvector` để tìm Rule khớp nhất trong Database.
* **Output:** Kịch bản phù hợp nhất: `"Rule matched: High late-night traffic indicates bot scraping. Suggested action: Check firewall logs."`

### Module 3: LLM Explainer (Tổng hợp & Báo cáo)
* **Tech:** `Groq API` (Llama-3-8b-8192).
* **Input:** Prompt tĩnh được nhét kết quả của Module 1 và 2. 
* **Output:** Văn bản trả lời cuối cùng để gửi cho sếp / webhook.

## 3. Lộ trình Triển khai & Cày Git (Execution Plan)

* **Phase 1 (Database Init & Data Layer):** Viết script Python kết nối PostgreSQL, tự động kích hoạt `CREATE EXTENSION IF NOT EXISTS vector`. Tạo bảng `time_series_data` và bảng `business_rules` (có cột kiểu `vector`). Tạo mock data cho cả 2 bảng.
* **Phase 2 (ML Layer):** Xây dựng `AnomalyDetector` class. Đọc dữ liệu từ bảng `time_series_data`, train `IsolationForest` và trả về danh sách các điểm anomaly.
* **Phase 3 (Vector Layer):** Xây dựng `SemanticRouter` class. Viết hàm nhận text lỗi, dùng `sentence-transformers` biến thành vector, và viết câu lệnh SQL query vào bảng `business_rules` dùng `<=>` để lấy kịch bản tương đồng nhất.
* **Phase 4 (LLM Layer):** Tích hợp Groq API, thiết kế Prompt Template nhận input từ Phase 2 và Phase 3.
* **Phase 5 (API & Assembly):** Gộp toàn bộ vào `FastAPI` và làm giao diện `Streamlit` để trigger luồng chạy.

---
**@Claude:** Confirm your understanding of this PostgreSQL-centric blueprint. Outline your development plan. DO NOT write code yet.

---

## ⚠️ Architecture Pivot (2026-04-25)

**Vector storage moved from `pgvector` to `ChromaDB`.** PostgreSQL 18 on Windows did not ship pgvector binaries and the install cost (VS Build Tools or manual binary copy with admin rights) was not justified for a local MVP.

The pipeline above still describes the original design intent. The actual implementation is hybrid:
- **PostgreSQL** continues to own time-series data (Module 1 input).
- **ChromaDB PersistentClient** (local `.chroma/` dir, owned by Phase 3) replaces pgvector for rule embeddings + cosine k-NN.

`SemanticRouter.route()` keeps the same I/O contract — only the backend differs. See `PLAN.md` §10 for full pivot details.