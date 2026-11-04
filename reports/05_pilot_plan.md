# 05 — Kế hoạch pilot trên máy MSI (RTX 5090, WSL2)

Mọi lệnh ở đây là **[UNVERIFIED — chưa chạy trên phần cứng đích]**. Phiên bản driver, CUDA, PyTorch, vLLM và model
phải được kiểm trên chính máy đó. Thứ tự bắt buộc: **chú thích xong trước, chạy G2⁺ sau** (`docs/ANNOTATION_GUIDELINES.md` §5).

## 1. Chuẩn bị môi trường (WSL2 Ubuntu)

1. Kiểm tra GPU:

   ```bash
   nvidia-smi
   ```

   RTX 5090 là kiến trúc Blackwell. Bản PyTorch dùng phải hỗ trợ compute capability (12, 0) — **[UNVERIFIED]**: cần
   bản build CUDA ≥ 12.8.

2. Repo và môi trường dự án (Python 3.11):

   ```bash
   git clone https://github.com/Thuy-g/paper3-kg-conflict-rerank && cd paper3-kg-conflict-rerank
   ```

   ```bash
   git checkout claude/paper3-audit-20261102
   ```

   ```bash
   make install && make test && make smoke
   ```

3. Kiểm tra PyTorch thấy đúng GPU (cần ra `(12, 0)`):

   ```bash
   python -c "import torch; print(torch.cuda.get_device_capability())"
   ```

4. vLLM trong một venv **riêng** (tránh xung đột phụ thuộc với project):

   ```bash
   vllm serve <model 7–8B instruct> --port 8000
   ```

   Ứng viên: một model instruct open-weight 7–8B. Licence, kích thước và việc vLLM có hỗ trợ trên Blackwell hay
   không đều là **[UNVERIFIED]**.

5. Kiểm tra server sống và trả lời được:

   ```bash
   curl -s http://localhost:8000/v1/models
   ```

## 2. Dữ liệu

- Fork CONFLICTS và Relink phải nằm cạnh repo (`../rag_conflicts`, `../Relink`), giống trong cloud; hoặc sửa đường
  dẫn trong config.
- Tái tạo đúng mẫu đã pre-register (deterministic):

  ```bash
  .venv/bin/python scripts/annotation/sample_items.py --config configs/annotation_v1.yaml
  ```

  So sánh danh sách `items` trong manifest mới với `manifests/annotation_sample_v1.json` đã commit; chúng phải trùng
  khớp.
- Wikidata: dùng slice nhỏ (`make slices`) để kiểm tra pipeline. Cho pilot thật, cần một view Wikidata phủ các entity
  của 109 câu hỏi; tạo bằng `build_reference_slice.py` với danh sách seed mới, hoặc từ JSON dump có ngày cố định (§4).

## 3. Các bước pilot

1. **Pilot annotation (bạn + A2)**: 40 item → codebook v1 (freeze, commit).
2. **Main annotation**: A1 400 item, A2 120 item → `submit.py` → `agreement.py` → `adjudicate.py` → `export_gold.py`.
3. **Baseline trên pool đầy đủ** (109 câu, 998 passage):
   - BM25;
   - random (5 seed);
   - LLM filter (`llm_judge`, `configs/pilot_msi.example.yaml`);
   - LLM-only typer với prompt `conflict_detection` của MemGraphRAG (MIT; cần ghi attribution) — **chưa cài**, việc
     của bước tiếp.
4. **Đo**:
   - FCFR/GER/WFR theo reason;
   - SD giữa các seed;
   - MDE ở N = 109 câu hỏi.

   → Pre-register ngưỡng go/no-go (`04` §3) **trước** bước 5.
5. **G2⁺ S0–S3** trên tập chú thích, với cùng LLM cho extraction/fallback. Báo cáo coverage của bước KG, số LLM call,
   decision metrics (B.5) và metric xếp hạng.

## 4. Vấn đề mở cần bạn quyết trước bước 5

- **Question frame cho dữ liệu tự nhiên.**
  - G2⁺ cần `(subject QID, property PID, time anchor)` cho mỗi câu hỏi. CONFLICTS/2Wiki không có sẵn (2Wiki có
    `evidences` dạng triple nhưng không có QID).
  - Phương án:
    - (a) LLM parse câu hỏi + linking vào Wikidata (tự động, có lỗi; đo riêng độ chính xác trên một mẫu kiểm tay);
    - (b) bạn gán frame bằng tay, **độc lập và không nhìn nhãn passage**.
  - Phương án nào thì frame cũng là input của method, không phải gold label.
- **Pin Wikidata.** Pin theo `lastrevid` từng entity (đã kiểm: tái lập từng byte), hoặc dùng JSON dump có ngày cố định
  + sha256 cho view lớn hơn.
- **Model LLM.** Chọn một model, ghi revision/hash; giữ cố định cho mọi system.

## 5. Phương án theo VRAM

| Cấu hình | Gợi ý | Ghi chú |
|---|---|---|
| 32 GB (RTX 5090) | model 7–8B ở bf16 | trọng số khoảng 15–16 GB; phần còn lại cho KV cache. Ước lượng thô, **[UNVERIFIED]** |
| 24 GB | model 7–8B lượng tử hóa 4-bit (AWQ/GPTQ) hoặc model nhỏ hơn | ghi rõ khác biệt model khi so sánh; không trộn kết quả hai cấu hình |
| MacBook M4 (24 GB) | chỉ chạy annotation tooling, test, smoke | không có CUDA; không chạy vLLM |
