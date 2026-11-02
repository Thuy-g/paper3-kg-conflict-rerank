# Kế hoạch Phase A–C

> Paper 3 — *Relation-Aware Evidence Reranking for Reliable RAG under Noisy and Conflicting Evidence*.
> Branch: `claude/paper3-audit-20261102` (giữ nguyên cho cả 3 phase, 1 Pull Request ở cuối Phase C).
> Đây là kế hoạch cho **prototype**; không phase nào tạo ra kết quả thí nghiệm.

## 0. Ràng buộc đã kiểm ở Phase 0 (chi tiết: `reports/00_environment.md`)

| Ràng buộc | Hệ quả cho kế hoạch |
|---|---|
| 4 vCPU, ~15 GiB RAM, không GPU | chỉ audit + prototype CPU; LLM mặc định là `MockLLM` |
| Trang web GitHub của upstream trả 403 (`GitHub access to this repository is not enabled for this session`) | **Kết quả Phase A:** `git clone --depth 1` cả 7 upstream đều thành công; HEAD trùng fork `Thuy-g/*` (`reports/02_codebase_map.md` §1) |
| `arxiv.org` bị chặn (proxy CONNECT 403; WebFetch cũng không resolve được) | không đọc được nội dung paper → claim về paper chỉ dựa vào README/code, còn lại ghi **[UNVERIFIED]** |
| `www.wikidata.org` bị chặn | `TinyKG` và bảng alias/hierarchy là fixture viết tay, ghi `synthetic` |
| PyPI, `huggingface.co` truy cập được | cài package được; tiny slice dataset từ HF khả thi (Phase B) |
| `conflicts.jsonl` (CONFLICTS) = 46.7 MB / 458 dòng | slice phải giới hạn theo dung lượng (≤ 50 MB tổng), không chỉ theo số ví dụ |

---

## Phase A — AUDIT (chỉ đọc)

### Mục tiêu
Hiểu 7 codebase đủ sâu để (1) biết phần nào tái dùng được làm baseline/evaluator trên
**fixed candidate evidence pool**, và (2) xác định **research gap** có bằng chứng từ code.

### Các bước
| # | Bước | Cách làm |
|---|---|---|
| A1 | Thử clone upstream | `git clone --depth 1 <upstream_url> third_party/<Repo>` cho cả 7 URL; lưu nguyên văn stdout/stderr + exit code |
| A2 | Fallback sang fork | nếu A1 lỗi: `git clone --depth 1 file:///home/user/<Repo> third_party/<Repo>` (fork đã attach); ghi commit hash; kiểm HEAD của branch fork có trùng branch mặc định của fork không; "fork == upstream" ghi **[UNVERIFIED]** |
| A3 | Inventory tự động | script stdlib trong `scripts/audit/`: nhận diện LICENSE, cây thư mục (depth ≤ 3), số dòng code, index mọi `def`/`class` kèm số dòng (dùng `ast`) để trích `path:line` chính xác |
| A4 | Component map | với mỗi repo, đọc code (không chỉ README) và map 6 nhóm: data loading / retrieval / KG construction & triple extraction / conflict detection & filtering / LLM backend / evaluation → `path:line` + tên hàm/class + mô tả 1–2 dòng; nhóm nào không có thì ghi "không có" |
| A5 | Trả lời (a)–(d) | xem bên dưới; mỗi câu kết luận rõ **Có / Không / Có điều kiện** + trích code |
| A6 | Kiểm paper | arXiv bị chặn → thử WebSearch (chỉ lấy title/venue/tác giả từ kết quả tìm kiếm); không xác nhận được thì ghi **[UNVERIFIED]** |
| A7 | Kiểm trích dẫn | `scripts/audit/check_citations.py`: parse các tham chiếu `path:line` trong `reports/01–03`, xác nhận dòng được trích có chứa đúng tên symbol; chạy trước khi commit |

Câu hỏi bắt buộc:
- **(a) GraphRAG-Bench**: schema JSON đầu vào của `Evaluation/retrieval_eval.py` và
  `Evaluation/generation_eval.py` (`context` là string hay list? retrieval eval có bắt buộc
  `generated_answer` không?); metric nào cần LLM judge; có trỏ `--base_url` sang vLLM local được
  không. Kết luận: có chấm được một standalone evidence reranker trên fixed candidate evidence
  pool mà không rebuild GraphRAG index không. (Nếu dependency nhẹ, có thể chạy phần parse input
  với 2–3 ví dụ tự tạo và một stub LLM; không gọi API thật.)
- **(b) TruthfulRAG**: `entropy_based_filter` — công thức, threshold, LLM được gọi ở bước nào;
  có tách ra làm baseline filter được không; liệt kê file trong `truthfulrag/` và `datas/`.
- **(c) MAGIC, CONFLICTS**: format dữ liệu (field, label set, kích thước, ví dụ rút gọn); bảng
  mapping sang schema chuẩn hóa của mình; có chuyển thành fixed pool cho reranking/typing được không.
- **(d) ArbGraph**: dựa trên code thực tế (pipeline atomization → claim alignment → evidence graph
  → conflict arbitration), đánh giá trung thực khả năng mở rộng thành bài journal ở IEEE Access /
  PLOS ONE / Scientific Reports: phần đóng góp mới cần có, tiêu chí venue (chỉ nêu những gì kiểm
  được, còn lại **[UNVERIFIED]**), rủi ro (trùng hướng với tác giả gốc, license, GPU). Không hứa
  hẹn khả năng "accept".

### Deliverables
- `reports/01_comparison_matrix.md` — ma trận repo × {bài toán, có KG không / dựng KG thế nào,
  cách xử lý conflict, có phân biệt apparent vs. genuine không, xử lý alias / granularity /
  temporal / homonym, LLM backend (API hay local), metric, dữ liệu, license, nhu cầu GPU, khả năng reuse}.
- `reports/02_codebase_map.md` — cho từng repo: trạng thái clone + lỗi nguyên văn, LICENSE và hệ
  quả reuse, commit hash, cây thư mục, component map có `path:line`; trả lời (a)–(d).
- `reports/03_candidate_gaps.md` — 5 gap: **G2** (KG-schema-aware apparent vs. genuine conflict
  typing → reranking), **G7** (empirical study về over-filtering), **G1** (KG-consistency reranker
  training-free), **G2+G1**, **G3+G8** (temporal / cross-lingual alias). Mỗi gap đủ 7 trường:
  unresolved problem; closest methods; bằng chứng còn mở (trích dẫn); contribution; GPU/API;
  minimal falsifiable experiment; điều gì làm mất novelty.

### Tiêu chí hoàn thành Phase A
- [x] 7/7 repo có trạng thái clone — cả 7 upstream clone thành công (exit 0), HEAD trùng fork.
- [x] Mỗi repo có: LICENSE + hệ quả reuse, commit hash, cây thư mục, component map đủ 6 nhóm.
- [x] (a)–(d) có kết luận rõ ràng và trích code `path:line` + tên symbol.
- [x] `check_citations.py` pass trên `reports/01–03` (104/104 OK).
- [x] Mọi claim về paper chưa kiểm được đều có **[UNVERIFIED]** (`02` §5, `03` §3).
- [x] `03_candidate_gaps.md` đủ 5 gap × 7 trường.
- [x] Không file nào trong `third_party/` hay trong các fork bị sửa (`git status` sạch).
- [x] Commit + push → **STOP POINT A**.

### Phase A+ — audit mở rộng (yêu cầu thêm sau STOP POINT A)

Phạm vi: audit 3 repo (`lei-nlp-lab/context_conflict_emnlp_2026`, `Parv17k/decision-models-conflict-typing`, `XMUDeepLIT/MemGraphRAG`), đọc 5 PDF
mới (CONFLICTS, ConflictRAG, HVM-GraphRAG, MemGraphRAG, EvoTrustRAG), trả lời câu hỏi mở rộng thành bài journal OA. Deliverable:
`reports/02b_extension_audit.md`, cùng cập nhật `00`, `01`, `02` §5 và `03` (đánh giá lại novelty của G2/G7).

- [x] 3/3 repo clone thành công; HEAD trùng fork (`git ls-remote`).
- [x] License, cây thư mục, component map 6 nhóm có `path:line` (`check_citations.py` pass).
- [x] Kiểm chứng các mục [search, UNVERIFIED] của Phase A bằng full text.
- [x] Câu trả lời (e) cho từng repo + khuyến nghị tổng hợp.
- [ ] Tính lại số liệu của decision-model typing từ output đã lưu — **bị chặn** (auto-mode classifier không cho chạy code bên thứ ba ở cloud).
- [x] Commit + push → **STOP**.

---

## Phase B — PROTOTYPE HARNESS (chạy CPU)

### Thiết kế package `src/kgrerank/`
| Module | Nội dung |
|---|---|
| `data/` | loader chuẩn hóa về `{qid, question, answers, candidates:[{pid, title, text, is_gold}], meta}`; ưu tiên 1–3 tiny slice: (1) 2WikiMultiHopQA (có evidence triples — rất hợp với KG; dataset id trên HF cần kiểm, **[UNVERIFIED]**) hoặc HotpotQA distractor (`hotpotqa/hotpot_qa`, config `distractor`), (2) CONFLICTS từ fork local, (3) tùy chọn MAGIC từ fork local. Nếu không tải được → fixture JSON viết tay trong `tests/fixtures/`, ghi `"synthetic": true`. Mỗi slice có manifest (nguồn, URL, license, sha256, số ví dụ, dung lượng) |
| `perturb/` | injection có seed cho 6 loại: `irrelevant`, `counterfactual` (genuine), `alias_historical_name`, `granularity`, `temporal_scope`, `homonym` |
| `rerankers/` | interface `Reranker.rerank(question, candidates)`; `BM25Reranker` (`rank_bm25`); `CrossEncoderReranker` chỉ khi tải được model < 100 MB (kiểm dung lượng qua HF API trước), nếu không thì stub báo lỗi rõ ràng |
| `llm/` | `LLMBackend` theo OpenAI-compatible interface; `MockLLM` (mặc định); `OpenAICompatLLM` (`http://localhost:8000/v1`); budget guard + token logging vào `logs/api_usage.jsonl` |
| `metrics/` | Recall@k, MRR, nDCG@k; EM/F1 (SQuAD normalization); **FCFR@k** = tỷ lệ passage `compatible` bị đẩy khỏi top-k hoặc bị filter; thêm breakdown theo `conflict_type` |
| `scripts/run_pilot.py` + `configs/*.yaml` + `Makefile` | `make test`, `make smoke` (< 2 phút CPU) |

### Quy ước nhãn (quyết định thiết kế — cần bạn xác nhận)
| `conflict_type` | `conflict_label` | Lý do |
|---|---|---|
| `none` (gold gốc) | `compatible` | evidence hỗ trợ answer |
| `none` (distractor gốc) | `irrelevant` | |
| `irrelevant` | `irrelevant` | passage lấy từ câu hỏi khác |
| `counterfactual` | `contradicting` | **genuine conflict**: answer bị thay bằng entity khác cùng type |
| `alias_historical_name` | `compatible` | khác surface form nhưng cùng entity (Edo ↔ Tokyo) |
| `granularity` | `compatible` | khác mức trong located-in / part-of hierarchy (Kyoto ⊂ Japan) |
| `temporal_scope` | `compatible` | giá trị khác nhưng đúng trong một khoảng thời gian khác (time qualifier không chồng lấn) |
| `homonym` | `irrelevant` | cùng tên nhưng là entity khác → không phải evidence, cũng không phải misinformation |

Hệ quả: FCFR chỉ đo over-filtering trên gold + alias + granularity + temporal_scope; với
`homonym` (và `predicate_mismatch` ở Phase C) sẽ đo riêng "tỷ lệ bị gán nhầm là genuine".
Lưu ý: perturbation `alias` / `granularity` / `temporal_scope` / `homonym` cần tri thức KG về
answer entity; vì Wikidata bị chặn, trên cloud chỉ áp dụng được cho câu hỏi có answer nằm trong
bảng tri thức viết tay (fixture) — số câu áp dụng được sẽ được báo cáo, không ngoại suy.

### Tiêu chí hoàn thành Phase B
- [ ] `pyproject.toml` pin version chính xác; `make install && make test` pass trên Python 3.11; `ruff check` sạch.
- [ ] `make smoke` chạy xong < 120 s trên 4 vCPU (đo bằng `time`), output có nhãn "smoke test on toy data – not a result".
- [ ] Loader: ≥ 1 nguồn (slice thật nếu tải được, nếu không thì fixture synthetic); test kiểm schema; tổng slice ≤ 200 ví dụ/dataset và ≤ 50 MB; có manifest.
- [ ] Perturb: cùng seed → output giống hệt, khác seed → khác; mỗi loại trong 6 loại có ≥ 1 test; nhãn đúng bảng trên.
- [ ] Reranker: test BM25; cross-encoder chạy được (model < 100 MB đã kiểm) hoặc stub + test bị skip có lý do.
- [ ] LLM: test `OpenAICompatLLM` từ chối endpoint không-local khi thiếu biến môi trường; test ghi JSONL; test không dùng network (mock HTTP).
- [ ] Metrics: test với giá trị tính tay cho Recall@k, MRR, nDCG@k, EM/F1, FCFR@k.
- [ ] Commit + push → **STOP POINT B**.

---

## Phase C — IDEA SKELETON (prototype, không phải kết quả)

### Thiết kế
- `kg/TinyKG` (từ fixture): entity type (P31-like), subclass (P279-like), located-in (P131-like),
  part-of (P361-like), alias kể cả historical name có thời gian hiệu lực (Saigon ↔ Ho Chi Minh City,
  Bombay ↔ Mumbai, Edo ↔ Tokyo), fact có qualifier start/end. API dự kiến: `resolve(name)`,
  `types(eid)`, `is_a(eid, cls)`, `located_in_ancestors(eid)`, `facts(s, p, at=None)`.
- `extract/`: `TripleExtractor` (`MockExtractor` pattern-based + `LLMExtractor` với prompt yêu cầu
  JSON, validate schema, dùng `LLMBackend`); `EntityLinker` dựa trên alias table, có ràng buộc type.
- `conflict/ConflictTyper` (rule-based) so sánh claim của passage với claim tham chiếu, thứ tự luật:
  `homonym` (subject khác entity) → `predicate_mismatch` → `none` (trùng sau chuẩn hóa) → `alias`
  → `granularity` → `temporal_scope` → `genuine`; trả về
  `{type, evidence: [KG facts], confidence}`.
- `conflict/ConflictAwareReranker`: `score = relevance − λ · penalty`, penalty **chỉ** khi
  `type == genuine` (tỷ lệ với `confidence`), kèm KG facts làm lời giải thích. Claim tham chiếu:
  (i) consensus của pool sau khi chuẩn hóa apparent conflict, hoặc (ii) fact trong KG nếu có —
  cả hai mode được cài để so sánh; giới hạn đã biết: consensus sai khi misinformation chiếm đa số.

### Deliverables
`src/kgrerank/{kg,extract,conflict}/`, unit test cho từng loại conflict, smoke test CPU,
`reports/04_ranked_recommendation.md`, `reports/05_pilot_plan.md` (pilot 300 câu trên RTX 5090 +
WSL2: venv, PyTorch build CUDA ≥ 12.8, kiểm `torch.cuda.get_device_capability() == (12, 0)`,
`vllm serve <model 7–8B instruct>`, `scripts/run_pilot.py`; phương án 32 GB và 24 GB),
`reports/06_compute_estimates.md`, `reports/07_uncertainties.md`, `HANDOFF.md`, Pull Request.

### Tiêu chí hoàn thành Phase C
- [ ] Fixture `TinyKG`: ≥ 3 alias (có historical name + thời điểm đổi tên), chuỗi located-in ≥ 3 cấp, ≥ 1 fact có start/end, ≥ 1 cặp homonym khác P31 type, ≥ 1 cặp predicate liên quan.
- [ ] Unit test: mỗi type trong 7 type (`alias`, `granularity`, `temporal_scope`, `homonym`, `predicate_mismatch`, `genuine`, `none`) có ≥ 1 test positive và ≥ 1 test near-miss negative.
- [ ] Smoke test: BM25 vs. ConflictAwareReranker trên toy fixture (Recall@k, MRR, nDCG@k, FCFR@k), có nhãn "smoke test on toy data – not a result".
- [ ] `04`: xếp hạng G1/G2/G7/G2+G1/G3+G8 theo novelty risk, tính khả thi trên 1× RTX 5090, thời gian tới kết quả đầu tiên, khả năng publish.
- [ ] `05`: lệnh chính xác, ghi rõ **[UNVERIFIED — chưa chạy trên phần cứng đích]**; có phương án 32 GB và 24 GB.
- [ ] `06`: ước tính dựa trên công thức + giả định ghi rõ (số câu × pool size × số LLM call × token).
- [ ] `07`: gom mọi **[UNVERIFIED]** + verification task (làm ở đâu, bằng lệnh gì).
- [ ] `HANDOFF.md`: checkout branch hoặc `claude --teleport`, `make test`, trỏ sang vLLM local, những gì chưa làm.
- [ ] Mở Pull Request `claude/paper3-audit-20261102` → `main` → **DỪNG**.

---

## Rủi ro chính và cách xử lý
| Rủi ro | Cách xử lý |
|---|---|
| Không đọc được paper (arXiv bị chặn) | dựa vào README/code; ghi [UNVERIFIED]; nếu cần trích section paper, bạn mở `arxiv.org` trong Network access của environment |
| Fork có thể khác upstream | ghi commit hash của fork; "fork == upstream" là [UNVERIFIED] |
| Dataset id trên HF không đúng/không truy cập được | fallback HotpotQA distractor → fixture synthetic |
| Cross-encoder > 100 MB hoặc không tải được | kiểm dung lượng trước; nếu vượt thì stub |
| Fixed pool từ dataset có sẵn hầu như không có apparent conflict tự nhiên | dùng perturbation có kiểm soát; ghi rõ là threat to validity |
| Số liệu toy bị hiểu nhầm là kết quả | nhãn bắt buộc trong mọi output + report |

## Ước tính chi phí
- Phase A: chỉ đọc code + script nhỏ; CPU không đáng kể; không tải dữ liệu.
- Phase B: cài package (vài phút); tiny slice vài MB. Nếu làm `CrossEncoderReranker` thật sẽ cần
  `torch` bản CPU + `sentence-transformers` + model MiniLM-L6 — dung lượng sẽ được kiểm trước khi
  tải; nếu bước nào dự kiến > 5 phút CPU sẽ dừng hỏi bạn.
- Phase C: CPU không đáng kể; không gọi API trả phí.
