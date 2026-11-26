# HANDOFF — Paper 3 (sau vòng pre-pilot review, 2026-11-05)

Repo này là **research prototype**; chưa có số liệu nào là kết quả thí nghiệm.
- Quy tắc làm việc: `CLAUDE.md`.
- Kế hoạch: `docs/PLAN.md` (vòng này: C.1, C.2).
- Báo cáo vòng này: `reports/08_prepilot_review.md`.

## 1. Trạng thái

| Phần | Trạng thái | Ở đâu |
|---|---|---|
| Audit 18 paper, 15 repo | xong | `reports/01`–`03`, `02b`–`02d` |
| Harness trung lập với method | xong, có test; vòng này thêm accounting LLM, metric condensed, cluster bootstrap | `src/kgrerank/`, `reports/03b`, `reports/08` |
| Mẫu chú thích v1 (pre-register, 440 item) | giữ nguyên; **chưa chú thích** | `manifests/annotation_sample_v1.json` |
| Codebook | **v0.1 (draft)** cho pilot; v0 giữ để lưu lịch sử | `docs/annotation/codebook_v0.1.md`, `CHANGELOG.md` |
| Annotator | A1 = bạn (dự kiến); **A2: TBD** | `docs/annotation/A2_quickstart.md` |
| Question frame | tooling xong (LLM parse + linking, audit); **chưa chạy với model thật** | `src/kgrerank/frames/`, `scripts/frames/` |
| G2⁺ | `policy_v0.2`, có test; **chưa đánh giá trên dữ liệu thật** | `src/kgrerank/conflict/` |
| Model trên MSI | config `Qwen/Qwen3-8B` (revision pin, BF16, non-thinking); **chưa thử trên MSI** | `configs/msi/` |

## 2. Trình tự đã khóa

1. Sửa protocol và integration — **xong (vòng này)**.
2. Pilot annotation 40 item với A1/A2.
3. Sửa codebook, rồi freeze thành v1.
4. Engineering pilot trên MSI, chỉ trên tập pilot (12 câu hỏi, không trùng main).
5. Main annotation, rồi evaluation theo kế hoạch đã khóa.

Main set **không bao giờ** được dùng để chọn prompt, policy, λ hay threshold. Chi tiết:
`docs/ANNOTATION_GUIDELINES.md` §12.

## 3. Bắt đầu annotation (làm được ngay, trên MacBook hoặc MSI)

1. Cài đặt (cần Python 3.11 và `uv`):

   ```bash
   git clone https://github.com/Thuy-g/paper3-kg-conflict-rerank && cd paper3-kg-conflict-rerank
   ```

   ```bash
   git checkout claude/paper3-audit-20261102
   ```

   ```bash
   make install && make test
   ```

2. Đặt hai fork `rag_conflicts` và `Relink` cạnh repo (`../rag_conflicts`, `../Relink`), rồi tạo lại sheet:

   ```bash
   make annotation-sample
   ```

   - Lệnh này ghi các file sheet vào `data/` (gitignored) và **không bao giờ** sửa manifest.
   - Nó phải in `pre-registered sample reproduced: identical items`. Nếu in `MISMATCH`, dừng lại và báo.
   - Nếu `data/annotation/v1` đã có sẵn, dùng
     `.venv/bin/python scripts/annotation/sample_items.py --config configs/annotation_v1.yaml --rebuild-data`.
3. Đọc `docs/annotation/codebook_v0.1.md` (khoảng 15 phút). Điểm mới so với v0:
   - thiếu ngày tháng thì thời gian là unknown, không phải "cùng thời điểm";
   - `CONTRADICTING` cần đủ ba điều kiện;
   - một predicate khác có thể là bridge fact.
4. Điền `data/annotation/v1/sheets/pilot_A1.csv` (40 item):
   - làm một mình;
   - không dùng LLM, web hay Wikidata;
   - không mở `key.jsonl` hay `manifests/`.
5. Nộp:

   ```bash
   .venv/bin/python scripts/annotation/submit.py --sample-dir data/annotation/v1 --set pilot --annotator A1 --codebook v0.1 --file data/annotation/v1/sheets/pilot_A1.csv
   ```

6. **A2: TBD.**
   - Khi có A2, chỉ đưa cho người đó `docs/annotation/A2_quickstart.md`, codebook v0.1 và `pilot_A2.csv`.
   - A2 nộp bằng lệnh trên với `--annotator A2` và file của A2.
   - Chưa có A2 thì bạn có thể thử sheet của mình (usability trial). Kết quả đó **không** được báo cáo như pilot hai
     annotator hay IAA.
7. Khi cả hai đã nộp:

   ```bash
   .venv/bin/python scripts/annotation/agreement.py --sample-dir data/annotation/v1 --set pilot
   ```

   Sau đó sửa codebook, freeze thành `codebook_v1.md` và ghi `CHANGELOG.md`.

## 4. Bước đầu tiên trên MSI (kiểm môi trường, không phải kết quả)

Mọi lệnh CUDA/PyTorch/vLLM dưới đây là **[UNVERIFIED — chưa chạy trên phần cứng đích]**. Không chạy gì trên main
set.

1. Repo và test, như §3 bước 1.
2. Cài vLLM trong một venv **riêng** (model card yêu cầu `vllm>=0.8.5`). Kiểm bản PyTorch/vLLM hỗ trợ RTX 5090
   (Blackwell); xem `reports/05` §1.
3. Chạy server với revision đã pin. Lần đầu sẽ tải khoảng 16,4 GB weights (5 file safetensors, theo metadata HF):

   ```bash
   vllm serve Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218 --dtype bfloat16 --max-model-len 8192 --max-num-seqs 8 --port 8000
   ```

4. Ghi lại môi trường (chạy trong venv của vLLM; file không chứa secret, có thể commit):

   ```bash
   python scripts/msi/record_env.py --out manifests/msi_env.json
   ```

5. Kiểm non-thinking bằng một request:

   ```bash
   curl -s http://localhost:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{"model": "Qwen/Qwen3-8B", "messages": [{"role": "user", "content": "Reply with the word OK."}], "max_tokens": 32, "chat_template_kwargs": {"enable_thinking": false}}'
   ```

   - Reply không được chứa `<think>`.
   - Nếu server từ chối trường `chat_template_kwargs`, hoặc reply có `<think>`, thì dừng và ghi lại lỗi. Trường này
     là **[UNVERIFIED]**.
6. Kiểm parser frame trên **12 câu hỏi pilot**:

   ```bash
   .venv/bin/python scripts/frames/parse_frames.py --config configs/msi/frames_pilot_qwen3.yaml
   ```

   - Cần `data/annotation/v1` trên MSI (chạy `make annotation-sample` như §3 bước 2).
   - Xem `llm_usage.by_status` trong `outputs/frames/frames_v1_pilot_run.json`: `parse_error`, `truncated`,
     `thinking_output` và `backend_error` phải gần 0.
   - Nếu bạn chưa nộp pilot của mình, chỉ xem các số đếm này, không mở nội dung frame.
   - Chưa có KG view phủ mention của câu hỏi (`reports/05` §4) thì đổi `kg_view` sang
     `data/wikidata_slice/kgview.json`. Khi đó phần lớn mention sẽ `unlinked`; đó là điều bình thường.
7. Engineering pilot đầy đủ (`configs/msi/engineering_pilot.yaml`) chỉ chạy **sau** khi pilot đã adjudicate,
   export (`export_gold.py --set pilot`) và codebook v1 đã freeze.

## 5. Chưa làm (cố ý)

- Annotation thật: cần người; LLM không điền trước và không tạo gold label.
- KG view phủ mention của 121 câu hỏi (pilot + main): cần cho G2⁺ thật; xây trên MSI.
- LLM-only typer theo prompt MemGraphRAG: còn là baseline dự kiến.
  - Prompt đó làm việc trên triple và không bao giờ trả IRRELEVANT, nên cần adapter.
  - Phải kiểm prompt, input và attribution MIT trước khi dùng (`reports/07` §2).
- Cross-encoder thật và generator cho EM/F1.
- Literature search có hệ thống cho novelty (`reports/07` §1).
- Nhánh DBpedia: chỉ chạy nếu phần chính thành công.

## 6. Nguyên tắc đã thống nhất

- Wikidata là primary reference KG; constraint chỉ là soft evidence.
  - Single-best-value không bao giờ tạo conflict.
  - Thiếu evidence về tính độc quyền, scope hay qualifier thì → `UNKNOWN`/fallback.
- Policy chỉ đổi qua version mới, có giải thích, **trước** khi xem kết quả G2⁺ trên dữ liệu tự nhiên.
- S3 chỉ là upper-bound diagnostic (có quyền truy cập answer fact); kết quả chính dùng S0–S2.
- Inference không bao giờ nhận reference answer, nhãn gold, cờ supporting fact hay annotation reasons.
- Frame do người sửa chỉ dùng cho human-framed diagnostic, báo cáo riêng.
- G7 → G2⁺ vẫn là working hypothesis. Synthetic perturbation chỉ là stress test.
- Ngưỡng 10 điểm % / 2 điểm % / 50% không phải tiêu chí khoa học cố định.
- Complementary (44 passage của main từ 6 câu hỏi) chỉ là exploratory.
