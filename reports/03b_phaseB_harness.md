# 03b — Phase B: method-neutral evaluation harness

Ngày 2026-11-04. Mọi con số trong báo cáo này là **smoke test on toy data – not a result**.

## 0. Tóm tắt

1. **Harness đã chạy được và trung lập với method** (không có G2⁺). Kiểm tra:
   - `make test`: 54 test pass, offline;
   - `make lint`: sạch;
   - `make smoke`: 0,4 s;
   - plumbing run trên 453 ví dụ thật: 4 s.
2. **Schema v1 tách decision khỏi reason.** Label protocol v0 chỉ gán decision khi đủ evidence, nếu không thì
   `UNKNOWN`. Có test cho thấy **cùng reason, khác evidence ⇒ khác decision**.
3. **Ba slice thật + một Wikidata reference slice** đã tạo, đúng giới hạn; manifest được commit, data thì không:
   - 2Wiki: 200 ví dụ;
   - CONFLICTS: 200 ví dụ;
   - Ragability: 53 dòng — toàn bộ corpus;
   - Wikidata: 200 ID, 1,06 MB.
4. **Phát hiện quan trọng nhất: FCFR không xác định được trên dữ liệu tự nhiên.** Không slice thật nào có nhãn
   apparent-conflict ở mức passage (§5.1). Muốn kiểm G7/G2⁺ cần một tập chú thích mức passage, độc lập với KG.
   Đây là việc của bạn ở Phase C/pilot, không phải lỗi của harness.

## 1. Đã xây gì (`src/kgrerank/`)

| Module | Nội dung | Ghi chú |
|---|---|---|
| `schema.py` | `Decision`, 11 reason type, `Candidate`/`Example`, validation, JSONL I/O | chặn: gold-CONTRADICTING; `unlabelled` khác UNKNOWN; perturbation không evidence |
| `signals.py` | 6 signal độc lập (`SignalBundle`), mỗi signal có `basis` | không có trường `decision`; chỉ là container cho Phase C |
| `kg/time.py` | time value Wikidata có precision; `temporal_relation` 3 trạng thái | endpoint thiếu = *unknown*, không phải *open*; một thời điểm (point) được xử lý riêng |
| `kg/view.py` | `KGView` (format `kgview/v1`): rank, qualifier, constraint (type/status/separators/exceptions), inverse (P1696 **và** Q21510855+P2306), subproperty | dùng chung cho fixture và Wikidata slice |
| `perturb/operators.py` | 9 operator + label protocol v0 (`docs/PLAN.md` B.3) | claim về fact được hỏi neo vào thời điểm của câu hỏi ("In 2010, …") |
| `rerankers/` | identity, random (seed), BM25 (Python thuần), cross-encoder (lazy, tùy chọn), oracle (chỉ để kiểm metric, chạy trên base ranking), LLM judge baseline | tie-break theo `pid` |
| `llm/` | `MockLLM`, `OpenAICompatLLM` (transport inject được), budget guard, token log | dừng **trước** khi vượt cap; key không bao giờ vào log |
| `metrics/` | Recall/MRR/nDCG, EM/F1, FCFR (abs/paired/filter, theo reason), GER, WFR (EvoTrustRAG Eq. 8 [p.10]), decision metrics, bootstrap, paired bootstrap, McNemar exact, Holm, MDE | đơn vị là query; metric không xác định = `None`, kèm số query dùng được |
| `pipeline.py`, `scripts/run_pilot.py` | chạy system × seed, trung bình theo seed, CI, paired delta so với reference, McNemar cho WFR | mọi output mang nhãn từ config |

Script mạng (không test nào import):
- `scripts/wikidata/build_reference_slice.py`
- `scripts/data/fetch_ragability_slice.py`

Script offline: `scripts/data/slice_local_sources.py`. Toàn bộ chạy bằng `make slices`.

## 2. Quyết định thiết kế đáng chú ý

1. **FCFR/GER dạng paired là metric chính.**
   - Chỉ tính các passage mà ranking tham chiếu chỉ-theo-relevance (cùng scorer) đã đưa vào top-k. Tránh đổ lỗi
     cho method về passage vốn không được retrieve cao.
   - Bản `abs` vẫn được báo cáo kèm.
2. **WFR theo đúng EvoTrustRAG.** Eq. 8: 𝟙[G_keep ∩ G_filter ≠ ∅] trung bình theo query [paper p.10], với
   G_keep = passage COMPATIBLE. FCFR (mức passage, theo reason) và WFR (mức query) được báo cáo song song.
3. **Oracle chạy trên base ranking.** Lỗi phát hiện khi đọc smoke output: bản đầu xếp theo thứ tự pool gốc, làm
   oracle "drop_contradicting" có FCFR_paired > 0. Đã sửa. Test giờ kiểm hai cực: FCFR = 0 cho drop_contradicting,
   FCFR = 1 cho drop_any_reason.
4. **Claim phải cùng phạm vi thời gian với câu hỏi.** Lỗi phát hiện khi đọc passage sinh ra: câu hỏi "…in 2010?"
   mà passage counterfactual nói "is X" (hiện tại) thì không thực sự mâu thuẫn. Giờ operator viết "In 2010, … was X".
   Riêng homonym không neo (thời gian của entity kia không có trong evidence).
5. **So sánh thời gian ba trạng thái, có precision.** Lỗi phát hiện bởi test:
   - một năm (point) từng bị coi như khoảng có hai đầu độc lập, nên "2010 ⊂ 2005–2012" ra UNKNOWN;
   - đã sửa;
   - hai khoảng cùng chạm năm 2012 vẫn đúng là UNKNOWN.
6. **Ragability: nhãn tương đối.** Corpus không nói phía nào đúng (entity hư cấu). Decision được gán **tương đối
   với một reference side** (mặc định context_1, ghi trong `meta.reference`). Context có quan hệ `qn` (không đủ
   thông tin) → UNKNOWN.

## 3. Dữ liệu (tất cả trong `data/`, gitignored; manifest trong `manifests/`)

| Slice | N | Kích thước | Licence | Nhãn mức passage |
|---|---|---|---|---|
| 2WikiMultiHopQA (từ `samples.json` của fork Relink, sha256 `dde3427d…`) | 200 | 1,2 MB | data **[UNVERIFIED]** (repo gốc Apache-2.0; fork Relink MIT) | gold = COMPATIBLE (`dataset`); 1.506 passage UNKNOWN; **0** apparent, **0** contradicting |
| CONFLICTS (`conflicts.jsonl`, sha256 `14559d5c…`) | 200 | 3,4 MB | repo Apache-2.0; text là trang web bên thứ ba | **toàn bộ UNKNOWN**; nhãn conflict chỉ ở mức query |
| Ragability (HF `ofai/RagabilityCorpus`, revision `2251634e…`) | 53 (toàn bộ corpus) | 0,1 MB | **CC-BY-SA-4.0**; attribution + share-alike ghi trong manifest | 157 COMPATIBLE, 50 CONTRADICTING (tương đối), 5 UNKNOWN; **0** apparent |
| Wikidata reference slice | 200 ID | 1,06 MB (gzip) | CC0 | không phải dữ liệu đánh giá; dùng cho KG view và kiểm constraint |
| Fixture synthetic (`tests/fixtures/`) | 6 câu, KG hư cấu 34 statement | nhỏ | nội bộ | đủ loại; `"synthetic": true` |

Manifest ghi:
- nguồn, sha256 của nguồn và của output;
- seed, index được chọn;
- script sha256, git HEAD;
- với nguồn mạng: từng request (URL, UTC, status, bytes, sha256).

Tổng `data/` ≈ 6,3 MB.

Phân bố nhãn query của CONFLICTS (toàn file 458 dòng):

| Loại | Số query |
|---|---|
| No conflict | 161 |
| Complementary information | 115 |
| Conflicting opinions and research outcomes | 115 |
| Conflict due to outdated information | 62 |
| Conflict due to misinformation | **5** |

Nhóm "outdated information" chính là vùng apparent-vs-genuine theo thời gian, khó nhất. Misinformation tự nhiên
rất hiếm.

## 4. Kiểm chứng

- 54 test offline, gồm:
  - schema;
  - time (precision, BCE, ba trạng thái);
  - `KGView`;
  - 9 operator: mỗi operator có ca đủ evidence và ca bắt buộc UNKNOWN;
  - BM25: giá trị tính tay 1,00459 / 0,61496 / 0,50229;
  - retrieval/QA/conflict/decision metrics: giá trị tính tay;
  - McNemar: 2/64, 22/1024; Holm; MDE 0,28016 với SD = 1, N = 100;
  - budget guard: từ chối endpoint không-local, dừng trước khi gọi;
  - token log không chứa key;
  - converter cho 3 nguồn;
  - smoke end-to-end;
  - kiểm tra **không** có chuỗi/code của WikiRecentChanges.
- `make smoke`: 0,4 s (< 120 s).
- Plumbing run `configs/pilot_local.yaml`: 453 ví dụ thật, 4 s.

Kết quả plumbing run trên 453 ví dụ thật (**smoke test on toy data – not a result**; chỉ để thấy metric nào xác định
được):

| Metric | BM25 | Ghi chú |
|---|---|---|
| recall@5 | 0,842 (n = 247 query có gold) | |
| `fcfr_paired@5` | **n/a** cho mọi system | không có passage apparent-compatible |
| `ger_paired@5` | 0 | chỉ có ở 50 query Ragability |
| `wfr` | 0 | 253 query |

## 5. Phát hiện ảnh hưởng tới hướng G7 → G2⁺

1. **Không có nhãn apparent-conflict tự nhiên ở mức passage** trong 2Wiki, CONFLICTS hay Ragability.
   - FCFR, metric lõi của G7, hiện chỉ đo được trên perturbation sinh từ KG, mà loại này dễ circular (`02d`
     §5.4).
   - **Đề xuất:** xây một tập chú thích mức passage, độc lập với KG, theo codebook decision/reason của schema v1.
   - Nguồn gợi ý: query "outdated information" và "complementary" của CONFLICTS, cùng các pool 2Wiki.
   - Cỡ (300–500 passage) và số annotator **cần bạn quyết**. Đây là điều kiện để G7 có bằng chứng.
2. **Cardinality constraint là signal yếu trên dữ liệu thật** (`02d` §2.1).
   - Phần lớn property quan hệ khai báo *single-best-value* (11/29), không phải single-value (2/29).
   - P19/P20 chỉ ở mức *suggestion*; exception lên tới 25.
   - Evidence phân biệt mạnh nhiều khả năng đến từ **qualifier thời gian và identity** (P1448 có ngày, alias, rank).
   - → Đề xuất đóng khung lại G2⁺ là "qualifier/identity-first, constraint làm prior mềm". Đây vẫn là giả thuyết.
3. **KG tự mâu thuẫn ở ranh giới thời gian.** Ví dụ ngày kết thúc của tên Saigon khác nhau theo ngôn ngữ.
   `temporal_overlap` phải cho phép UNKNOWN. Đánh giá nên báo cáo tỷ lệ UNKNOWN (coverage) cạnh accuracy.
4. **Ragability chỉ hợp cho GER/WFR và cho ca "KG không biết gì"** (entity hư cấu → G2⁺ phải trả UNKNOWN và chuyển
   sang LLM fallback). Không dùng nó để chứng minh xử lý apparent conflict.
5. **Ngưỡng.**
   - Harness đã có MDE, CI và SD giữa seed. Chưa đề xuất ngưỡng mới, vì chưa có pilot với reranker/LLM thật
     (MSI).
   - Lưu ý: "GER giảm ≤ 2 điểm %" cần kiểm định non-inferiority. Với N cỡ vài trăm query, rất có thể thiếu power;
     MDE từ pilot sẽ cho biết.

Không có phát hiện nào là **blocker** cho harness. Phát hiện 1 là điều kiện cần cho claim của paper, nên tôi nêu
lên trước khi sang Phase C.

## 6. Giới hạn đã biết

- Cross-encoder chưa cài, chưa test trong cloud (test bị skip theo thiết kế; extra `ce` được pin nhưng **chưa
  kiểm**).
- Pipeline chưa có generator nên EM/F1 mới chỉ có hàm + test, chưa dùng.
- BM25 tính IDF trong pool.
- Lịch Julian của Wikidata chưa quy đổi.
- Kiểm tra homonym dùng P31 nông (không suy luận P279).
- Item mô tả nhẹ trong Wikidata slice chỉ có P31/P131 truthy từ WDQS (sid `wdqs-truthy:…`).
- Kiểm tra "alias dùng chung" chỉ thấy entity có trong view.
- Prompt của LLM judge là bản trung lập v0. Prompt MemGraphRAG (MIT) theo `02b` §6.5 để Phase C.
- `MockLLM` chỉ kiểm plumbing: mọi số của `llm_judge_mock` vô nghĩa.

## 7. Cách chạy lại

Cài đặt, rồi chạy test, lint và smoke:

```bash
make install
```

```bash
make test
```

```bash
make lint
```

```bash
make smoke
```

Tạo lại các slice (cần mạng; chỉ ghi vào `data/` và `manifests/`):

```bash
make slices
```

Plumbing run trên slice thật (offline):

```bash
.venv/bin/python scripts/run_pilot.py --config configs/pilot_local.yaml
```
