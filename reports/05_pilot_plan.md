# 05 — Kế hoạch trên máy MSI (RTX 5090, WSL2) — cập nhật 2026-11-05

Mọi lệnh CUDA, PyTorch và vLLM ở đây là **[UNVERIFIED — chưa chạy trên phần cứng đích]**. Phiên bản driver, CUDA,
PyTorch và vLLM phải được kiểm và ghi lại trên chính máy đó (`scripts/msi/record_env.py`).

Báo cáo này không đưa ra con số throughput hay tổng thời gian chạy nào; chúng được đo ở engineering pilot.

Trình tự khóa (`docs/ANNOTATION_GUIDELINES.md` §12):
1. protocol;
2. pilot annotation;
3. freeze codebook v1;
4. engineering pilot trên **tập pilot**;
5. main annotation và evaluation.

## 1. Model: `Qwen/Qwen3-8B` (quyết định 2026-11-05)

Các thông tin dưới đây đã kiểm trong session ngày 2026-11-05 bằng model card và metadata của Hugging Face; không tải
weights. Config: `configs/msi/qwen3_8b.yaml`.

| Mục | Giá trị | Nguồn |
|---|---|---|
| Revision (pin) | `b968826d9c46dd6066d109eabc6255188de91218` | HF; sha256 của `config.json`, `generation_config.json`, `tokenizer_config.json`, `README.md` ghi trong config |
| Licence | Apache-2.0 | model card |
| dtype | BF16 | `config.json` (`torch_dtype`) |
| Dung lượng weights | 16.381.516.776 byte (khoảng 16,4 GB; 5 file safetensors) | HF API `tree/<revision>` |
| Non-thinking | chat template kiểm `enable_thinking is false` | `tokenizer_config.json` |
| Trường request để tắt thinking | `chat_template_kwargs: {enable_thinking: false}` — **[UNVERIFIED]**; trang qwen.readthedocs.io trả HTTP 403 qua proxy | — |
| Sampling khuyến nghị cho non-thinking | T = 0,7, top_p = 0,8, top_k = 20, min_p = 0 | model card, mục Best Practices |
| vLLM | `vllm>=0.8.5` | model card |

- **Một model, một revision cho mọi vai trò:** frame parse, extraction, fallback, LLM baseline. Chỉ prompt khác nhau
  theo vai trò.
- **Lỗi thinking:** reply nào chứa `<think>` bị harness đánh dấu `thinking_output`. Đó là lỗi, không phải `UNKNOWN`.
- **Decoding:** pilot dùng setting khuyến nghị (T = 0,7) với nhiều seed. Setting cho main (giữ T = 0,7 hay greedy)
  được chốt trong pre-registration sau engineering pilot, không chọn theo kết quả main.

## 2. Môi trường (WSL2 Ubuntu)

1. Kiểm tra GPU:

   ```bash
   nvidia-smi
   ```

   RTX 5090 là Blackwell, compute capability (12, 0). Bản PyTorch phải hỗ trợ kiến trúc này; cần bản build CUDA
   ≥ 12.8 **[UNVERIFIED]**.

2. Repo và môi trường dự án (Python 3.11), theo `HANDOFF.md` §3 bước 1.

3. vLLM trong một venv **riêng**, để tránh xung đột phụ thuộc với project. Kiểm PyTorch thấy đúng GPU (cần ra
   `(12, 0)`):

   ```bash
   python -c "import torch; print(torch.cuda.get_device_capability())"
   ```

4. Server: bắt đầu với context và batch nhỏ.

   ```bash
   vllm serve Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218 --dtype bfloat16 --max-model-len 8192 --max-num-seqs 8 --port 8000
   ```

5. Ghi lại môi trường; chạy trong venv của vLLM:

   ```bash
   python scripts/msi/record_env.py --out manifests/msi_env.json
   ```

6. Kiểm non-thinking bằng một request (`HANDOFF.md` §4 bước 5).

## 3. Dữ liệu và KG view

- **Mẫu chú thích:** `make annotation-sample` tái tạo đúng mẫu đã pre-register và không sửa manifest
  (`HANDOFF.md` §3).
- **KG view phủ mention (vấn đề mở, chưa cài).** G2⁺ ở S2 cần một Wikidata view chứa:
  - entity (label, alias) của subject trong câu hỏi và của các mention trong passage;
  - statement identity/hierarchy của chúng (P31, P279, P1448, P1449, P2561, P1813, P131, P361, P17);
  - metadata và constraint của các property được hỏi.

  Slice hiện có (`data/wikidata_slice/`, 200 ID) không phủ 121 câu hỏi. Đề xuất, **chưa cài và chưa kiểm**:
  1. lấy mention từ output của frame parser và extractor;
  2. tìm QID ứng viên bằng exact label/alias match qua WDQS. Giữ mọi ứng viên, kể cả homonym; không chọn hộ;
  3. tải entity bằng `Special:EntityData` với `lastrevid` (cách pin đã kiểm ở `02d` §2.1);
  4. đi lên tổ tiên theo P131/P361 với độ sâu giới hạn.

  View cho main phải được xây bằng pipeline đã khóa, trước khi xem kết quả main.
- **Snapshot thời gian** (`configs/frames_v1.yaml`):
  - CONFLICTS dùng `[2025-04-03, 2025-06-15]` (cận dưới từ dữ liệu, cận trên từ ngày arXiv v2) — **bạn cần xác nhận**;
  - 2Wiki không có snapshot, nên thời gian tương đối giữ `unresolved`.

## 4. Các bước

1. **Pilot annotation (A1 + A2)** → codebook v1 (freeze, commit). A2 đang là TBD.
2. **Engineering pilot (bước 4), chỉ trên tập pilot** (12 câu hỏi, 40 item, không trùng main):
   1. Frames:

      ```bash
      .venv/bin/python scripts/frames/parse_frames.py --config configs/msi/frames_pilot_qwen3.yaml
      ```

   2. Export pilot (sau adjudication):

      ```bash
      .venv/bin/python scripts/annotation/export_gold.py --config configs/annotation_v1.yaml --set pilot
      ```

   3. Chạy pilot:

      ```bash
      .venv/bin/python scripts/run_pilot.py --config configs/msi/engineering_pilot.yaml
      ```

   4. Đo:
      - tỷ lệ `parse_error`, `truncated`, `thinking_output`, `backend_error` theo vai trò;
      - token và latency;
      - SD giữa các seed;
      - coverage của frame.
   5. Dựa trên đo đạc ở bước 4.4, chốt trong pre-registration: decoding, `max_tokens`, `top_m`, `context_m`, λ,
      và ngưỡng go/no-go (`04` §3, phải ≥ MDE). Sửa prompt nào cũng tạo version mới, **trước** khi chạm main.
3. **Main (bước 5)**, sau khi main annotation đã export:
   1. frames cho main (`configs/msi/frames_v1_qwen3.yaml`);
   2. frame audit bằng người trên mẫu riêng: `frame_audit.py sample`, rồi `compare`;
   3. chạy `configs/msi/main_eval.example.yaml` với các giá trị đã khóa.

   Báo cáo:
   - coverage trên toàn tập, số LLM call theo vai trò, failure rate;
   - decision metrics với cluster bootstrap (B.5);
   - metric xếp hạng condensed;
   - S3 riêng, như upper bound;
   - human-framed diagnostic riêng.
4. **Baseline LLM-only typer theo MemGraphRAG** (dự kiến): prompt làm việc trên triple và không bao giờ trả
   IRRELEVANT, nên cần adapter. Phải kiểm prompt, input và attribution MIT trước khi dùng.

## 5. Phương án theo VRAM

| Cấu hình | Gợi ý | Ghi chú |
|---|---|---|
| 32 GB (RTX 5090) | Qwen3-8B BF16 | weights khoảng 16,4 GB (metadata HF); phần còn lại cho KV cache. Bắt đầu với `--max-model-len 8192 --max-num-seqs 8`. Mức dùng VRAM thật là **[UNVERIFIED]** |
| 24 GB | không nằm trong kế hoạch | bản lượng tử hóa là một model khác: kết quả phải tách riêng, không trộn |
| MacBook M4 (24 GB) | chỉ annotation tooling, test, smoke | không có CUDA; không chạy vLLM |
