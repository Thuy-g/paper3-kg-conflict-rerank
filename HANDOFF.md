# HANDOFF — Paper 3 (cuối Phase C, 2026-11-04)

Repo này là **research prototype**. Chưa có số liệu nào là kết quả thí nghiệm. Quy tắc làm việc: `CLAUDE.md`.
Kế hoạch: `docs/PLAN.md`.

## 1. Trạng thái

| Phần | Trạng thái | Ở đâu |
|---|---|---|
| Audit 18 paper, 15 repo | xong | `reports/01`–`03`, `02b`–`02d` |
| Harness trung lập với method (schema v1, metric, thống kê, LLM guard) | xong, có test | `src/kgrerank/`, `reports/03b` |
| Slice dữ liệu nhỏ + manifest | xong | `manifests/`, `make slices` |
| Protocol + tooling chú thích độc lập (400 item, pre-register) | xong; **chưa chú thích** | `docs/ANNOTATION_GUIDELINES.md`, `docs/annotation/`, `scripts/annotation/` |
| G2⁺ skeleton (KG-first, LLM fallback, S0–S3) | skeleton có test; **chưa đánh giá trên dữ liệu thật** | `src/kgrerank/{extract,conflict}/` |
| Báo cáo 04–07 | xong | `reports/04`–`07` |

## 2. Tiếp tục trên máy local

```bash
git clone https://github.com/Thuy-g/paper3-kg-conflict-rerank && cd paper3-kg-conflict-rerank
```

```bash
git checkout claude/paper3-audit-20261102
```

```bash
make install && make test && make smoke
```

- Cần Python 3.11 và `uv`.
- Đặt các fork `rag_conflicts`, `Relink` cạnh repo, giống bố cục trong cloud.
- Để mở lại session Claude Code trên web từ máy local, xem tài liệu Claude Code về teleport. Cờ `claude --teleport` là
  **[UNVERIFIED]**, chưa kiểm trong session này.

## 3. Việc của bạn, theo thứ tự

1. **Tạo lại mẫu chú thích** (deterministic; đối chiếu với `manifests/annotation_sample_v1.json`):

   ```bash
   .venv/bin/python scripts/annotation/sample_items.py --config configs/annotation_v1.yaml
   ```

2. **Pilot:**
   - bạn và annotator 2 điền `data/annotation/v1/sheets/pilot_A1.csv` và `pilot_A2.csv` theo
     `docs/annotation/codebook_v0.md`;
   - nộp bằng `submit.py --set pilot --codebook v0`;
   - chạy `agreement.py --set pilot`;
   - sửa codebook, freeze thành `codebook_v1.md`, ghi CHANGELOG, commit.
3. **Main:**
   - A1 điền `main_A1.csv` (400 item), A2 điền `main_A2.csv` (120 item);
   - lần lượt chạy `submit.py`, `agreement.py`, `adjudicate.py prepare` / `merge`, `export_gold.py`;
   - lệnh đầy đủ ở `docs/ANNOTATION_GUIDELINES.md` §5.
4. **Quyết các vấn đề mở** (`reports/07` §2):
   - question frame (D1);
   - mở rộng Complementary (D3);
   - model LLM.
5. **Pilot trên MSI** (`reports/05`):
   - chạy baseline trước;
   - pre-register ngưỡng;
   - sau đó mới chạy G2⁺ S0–S3.

## 4. Chưa làm (cố ý)

- **Annotation thật**: cần người; LLM không được làm gold annotator.
- **LLM-only typer** dùng prompt MemGraphRAG: baseline bắt buộc, cài ở bước pilot, có attribution MIT.
- **Cross-encoder thật và generator cho EM/F1.**
- **Literature search có hệ thống** cho novelty (`reports/07` §1).
- **Nhánh DBpedia** (C-staged): chỉ chạy nếu core thành công.

## 5. Nguyên tắc đã thống nhất (không đổi nếu bạn chưa quyết lại)

- Wikidata là primary reference KG; DBpedia chỉ là thí nghiệm cross-KG có điều kiện.
- Property constraint của Wikidata chỉ là soft evidence.
- G7 → G2⁺ vẫn là working hypothesis.
- Synthetic perturbation từ KG chỉ là stress test; bằng chứng chính là tập chú thích độc lập.
- Không chốt ngưỡng 10 điểm % / 2 điểm % / 50% trước pilot thật.
