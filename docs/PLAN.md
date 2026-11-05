# Kế hoạch Phase A–C

> Paper 3 — *Relation-Aware Evidence Reranking for Reliable RAG under Noisy and Conflicting Evidence*.
> Branch: `claude/paper3-audit-20261102` (giữ nguyên cho cả 3 phase, 1 Pull Request ở cuối Phase C).
> Đây là kế hoạch cho **prototype**; không phase nào tạo ra kết quả thí nghiệm.

## 0. Ràng buộc đã kiểm ở Phase 0 (chi tiết: `reports/00_environment.md`)

| Ràng buộc | Hệ quả cho kế hoạch |
|---|---|
| 4 vCPU, ~15 GiB RAM, không GPU | chỉ audit + prototype CPU; LLM mặc định là `MockLLM` |
| Trang web GitHub của upstream trả 403 (`GitHub access to this repository is not enabled for this session`) | **Kết quả Phase A:** `git clone --depth 1` cả 7 upstream đều thành công; HEAD trùng fork `Thuy-g/*` (`reports/02_codebase_map.md` §1) |
| `arxiv.org` bị chặn ở Phase 0; **từ Phase A+ truy cập được bằng `curl`** (WebFetch vẫn lỗi) | đọc full text paper; mục chưa kiểm vẫn ghi **[UNVERIFIED]** |
| Wikidata (kiểm lại 2026-11-04, `00_environment.md` §4): WDQS và `Special:EntityData` **truy cập được**; Action API trả **429** | tiny Wikidata reference slice (B.7) qua WDQS + `Special:EntityData`, tuần tự, có `sleep`; không dùng Action API; fixture viết tay vẫn dùng cho test offline |
| `downloads.dbpedia.org`: connection reset (2026-11-04); Databus metadata và `dbpedia.org/sparql` truy cập được | không tải file release DBpedia trong cloud (`02d` §3) |
| ACL Anthology (trang + PDF) truy cập được (2026-11-04) | đọc được paper ACL khi cần |
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

### Phase A++ — audit mở rộng đợt 3

Phạm vi: When Facts Change (`jwallat/knowledge-conflicts-mutability`), Ragability (`OFAI/python-ragability`, `OFAI/python-llms-wrapper`),
TimeR4 (`qianxinying/TimeR4`), PAGE-RAG (`CXY0112/PAGE-RAG`). Deliverable: `reports/02c_extension_audit_2.md`; cập nhật `01`, `02` §5, `03`, `CLAUDE.md`.

- [x] 5/5 repo clone thành công; HEAD trùng fork.
- [x] License, component map có `path:line` (`check_citations.py` pass).
- [x] Câu trả lời (f) cho 4 bài + bảng tổng hợp mọi công trình đã audit + gợi ý sơ bộ cập nhật (`02c` §7).
- [x] Ghi nhận lỗi quy trình: clone TimeR4 (858 MB data) mà không kiểm dung lượng trước → đã bổ sung quy trình vào `CLAUDE.md` §8.
  Sửa 2026-11-04: bước `git ls-tree -r -l` trên clone `--filter=blob:none` **tự tải mọi blob** (gây "RPC failed; curl 35") →
  quy trình mới chỉ dùng `ls-tree --name-only` + sparse checkout danh sách file cụ thể.

### Kiểm chứng trước Phase B (2026-11-04)

Deliverable: `reports/02d_kg_sources_and_constraints.md`, `reports/00_environment.md` §4, appendix B/C.

- [x] Network: ACL Anthology, Wikidata (WDQS, `Special:EntityData`, Action API = 429), HF, DBpedia
  (`downloads.dbpedia.org` connection reset → dừng phần phụ thuộc).
- [x] Tài liệu chính thức về P2302, Q19474404, Q52060874, Q21510857, subject/value type, inverse, P580/P582/P585.
- [x] DBpedia `infobox-properties`: generic vs mappings, nội dung, bảng kiểm 7 câu hỏi (Databus + mã DIEF + SPARQL).
- [x] Bảng KG/corpus của 18 paper đã audit; khuyến nghị A/B/C có các lần thử falsify.
- [x] Commit + push → **STOP**.

**Điều chỉnh Phase B (bạn duyệt ngày 2026-11-04, kèm 7 yêu cầu).** Kiểm chứng trước khi implement nằm ở
`reports/02d_kg_sources_and_constraints.md`. Phase B mới ở dưới **thay thế** thiết kế và quy ước nhãn cũ.

---

## Phase B — METHOD-NEUTRAL EVALUATION HARNESS (chạy CPU)

### B.0 Nguyên tắc (ràng buộc cứng)

1. **Trung lập với method.**
   - Phase B **không** implement G2⁺ (KG-first typing, LLM fallback).
   - Không có code nào kết hợp các signal thành decision.
   - G7 → G2⁺ chỉ là **working hypothesis**, chưa phải kết luận và chưa được khẳng định là novel.
2. **Decision tách khỏi reason.**
   - Decision ∈ {`COMPATIBLE`, `CONTRADICTING`, `IRRELEVANT`, `UNKNOWN`}.
   - Reason type ∈ {`alias`, `historical_identity`, `hierarchy`, `geographic_granularity`, `temporal_scope`,
     `entity_identity_mismatch`, `homonym`, `inverse_relation`, `predicate_mismatch`, `counterfactual`, `unknown`}.
   - Reason **không** tự quyết định decision. Thiếu context/qualifier ⇒ `UNKNOWN`.
   - Không có rule `homonym → IRRELEVANT` cố định.
3. **Constraint là guidance, không phải axiom** (`02d` §1).
   - Không có rule "single-value + hai object khác nhau ⇒ genuine contradiction".
   - Multi-value ≠ mutable; single-value ≠ stable.
4. **Sáu signal tách rời** (`02d` §2): `cardinality_constraint`, `mutability_class`, `temporal_overlap`,
   `qualifier_evidence`, `entity_identity`, `relation_semantics`.
   - Phase B chỉ định nghĩa **schema** của chúng.
   - Việc tính signal và kết hợp signal thuộc Phase C (G2⁺ skeleton).
5. **Ngưỡng là provisional engineering targets.**
   - Các ngưỡng FCFR@5 giảm ≥ 10 điểm %, GER@5 giảm ≤ 2 điểm %, LLM calls giảm ≥ 50% **không** phải tiêu chí
     thành công đã được biện minh.
   - Phase B cung cấp công cụ đo baseline variance, effect size, bootstrap CI và MDE (B.6).
   - Ngưỡng mới chỉ được đề xuất **sau pilot**, và được ghi (pre-register) **trước** khi chạy G2⁺.
   - Không tune method để đạt ngưỡng.
6. **Falsifiability.**
   - Báo cáo riêng theo các setting KG S0–S3 (`02d` §5.4).
   - Tập synthetic sinh từ Wikidata chỉ là capability probe.
   - Bằng chứng chính phải đến từ tập có nhãn độc lập với KG.
7. **Không dùng WikiRecentChanges** (repo `knowledge-conflicts-mutability` không có LICENSE): không code, không data.
   Paper chỉ được trích dẫn để làm động lực.

### B.1 Schema dữ liệu v1 (thay schema cũ trong `CLAUDE.md` §4)

```json
{"qid": "str", "question": "str", "answers": ["str"],
 "candidates": [{"pid": "str", "title": "str", "text": "str", "is_gold": false,
                 "decision": "COMPATIBLE|CONTRADICTING|IRRELEVANT|UNKNOWN",
                 "reasons": ["alias", "temporal_scope"],
                 "label_source": "dataset|perturbation_rule_v1|perturbation_rule_v0|manual|unlabelled",
                 "evidence": [{"kind": "kg_statement|kg_entity|kg_property|dataset_field|note",
                               "ref": "str", "detail": {}}]}],
 "meta": {"source": "str", "synthetic": false, "kg_derived": false, "license": "str"}}
```

- `reasons` là **danh sách**, có thể rỗng (không có bất đồng bề mặt) hoặc nhiều phần tử (ví dụ alias + temporal).
- `is_gold` là relevance dùng cho Recall/MRR/nDCG. Nguồn của nó được ghi trong `meta.relevance_source`
  (cập nhật 2026-11-05, `src/kgrerank/annotation/export.py`):
  - 2Wiki: `dataset_supporting_facts`. Judgment phủ toàn pool. Cờ của dataset được giữ riêng trong
    `meta.dataset_supporting_pids`, tách khỏi nhãn người.
  - CONFLICTS: `human_answer_support` (`answer_support = yes`). Chỉ phủ các passage đã chú thích; danh sách nằm
    trong `meta.relevance_judged_pids`.
- Validation chặn các trường hợp sau:
  - giá trị ngoài enum;
  - `reasons` trùng lặp;
  - `is_gold = true` mà `decision = CONTRADICTING`;
  - `label_source = perturbation_rule_v*` mà `evidence` rỗng.
- Dữ liệu chưa có nhãn mức passage (distractor 2Wiki, kết quả search của CONFLICTS) có `decision = UNKNOWN`,
  `label_source = unlabelled`. Không giả định distractor là `IRRELEVANT`.
- `meta.kg_derived = true` nếu dataset được xây từ Wikidata (2Wiki, ConflictBank, TimeQuestions, MAGIC). Báo cáo tách
  riêng theo cờ này.

**Schema signal** (`kgrerank/signals.py`, hợp đồng I/O cho Phase C, **không** nằm trong file dữ liệu gold):
- `SignalBundle` gồm 6 trường độc lập, mỗi trường `Optional`;
- mỗi giá trị mang `basis` (provenance: QID/PID/statement ID/rule);
- không có trường `decision`.

### B.2 Module

| Module | Nội dung |
|---|---|
| `schema.py` | enum, dataclass, validation, JSONL I/O |
| `signals.py` | dataclass cho 6 signal (chỉ là container, không có logic kết hợp) |
| `kg/view.py`, `kg/time.py` | `KGView` chỉ-đọc (entity, statement có rank và qualifier, property có constraint) nạp từ fixture hoặc từ Wikidata slice đã chuẩn hóa; interval có precision của Wikidata, so sánh 3 trạng thái (`overlap`/`disjoint`/`unknown`) |
| `data/` | converter offline từ file local: 2Wiki (định dạng gốc), CONFLICTS (`conflicts.jsonl`, dùng `short_text`/`snippet`), Ragability (rows HF) → schema v1 |
| `perturb/` | operator có seed, mang evidence; **label protocol v0** (B.3) |
| `rerankers/` | `Ranking` (thứ tự + tập bị loại); identity, random (seed), BM25 (Python thuần, tie-break theo `pid`), cross-encoder (lazy, tùy chọn; test bị skip nếu thiếu), oracle (**chỉ để kiểm metric**, gắn nhãn rõ), LLM passage judge baseline (qua `LLMBackend`, mặc định `MockLLM`) |
| `llm/` | `LLMBackend`, `MockLLM`, `OpenAICompatLLM` (stdlib HTTP), budget guard, `logs/api_usage.jsonl` |
| `metrics/` | retrieval, QA, conflict (B.4), typing (B.5), thống kê (B.6) |
| `scripts/wikidata/build_reference_slice.py` | WDQS (selection) + `Special:EntityData` (full statements); manifest |
| `scripts/data/fetch_ragability_slice.py` | ≤ 200 rows qua HF datasets-server; manifest có licence/attribution |
| `scripts/data/slice_local_sources.py` | 2Wiki (từ fork Relink) và CONFLICTS (từ fork) → ≤ 200 ví dụ; manifest |
| `scripts/run_pilot.py`, `configs/smoke.yaml`, `Makefile` | `make test`, `make lint`, `make smoke` |

- Raw data nằm trong `data/` (gitignored).
- Chỉ commit: script, `manifests/*.json` (chỉ metadata), fixture synthetic nhỏ.

### B.3 Label protocol cho perturbation (lúc xây dữ liệu; **không** phải method)

**v1 (2026-11-04):** `predicate_mismatch` chuyển từ `COMPATIBLE` sang `IRRELEVANT`, để khớp định nghĩa IRRELEVANT
của codebook ("không liên quan tới fact được hỏi"). Lý do: nếu để `COMPATIBLE`, FCFR sẽ phạt cả việc loại một
passage không giúp trả lời câu hỏi. Các dòng khác giữ nguyên như v0.

Mỗi operator ghi `reasons` theo **cái nó đã thay đổi**. `decision` chỉ được gán khi **mọi** điều kiện tiên quyết
có evidence trong `KGView`; nếu không thì `UNKNOWN`. Giá trị có rank `deprecated` không được dùng làm evidence
hỗ trợ.

| Operator | `reasons` | Decision nếu đủ điều kiện | Điều kiện tiên quyết (đều phải có evidence) |
|---|---|---|---|
| counterfactual | `counterfactual` | `CONTRADICTING` | v' cùng type (P31) với giá trị gold; v' không phải giá trị (bất kỳ rank, bất kỳ thời gian) của (s, p) và không phải alias của giá trị gold; câu hỏi có đúng một answer trong phạm vi thời gian của nó |
| alias | `alias` | `COMPATIBLE` | chuỗi thay thế là label/alias của **cùng QID**; quan hệ trong câu hỏi không phải quan hệ về tên (P1448, P1449, P2561, P1813, …) |
| historical name | `historical_identity` | `COMPATIBLE` | tên là giá trị P1448/P2561 của cùng QID **có** qualifier thời gian, và passage nêu khoảng thời gian đó; điều kiện về quan hệ tên như dòng alias |
| temporal scope | `temporal_scope` | `COMPATIBLE` | passage nêu giá trị v' **kèm** khoảng hiệu lực lấy từ P580/P582/P585, và khoảng đó khớp KG; không nêu khoảng thời gian ⇒ `UNKNOWN` |
| granularity | `geographic_granularity` hoặc `hierarchy` | `COMPATIBLE` | v' là tổ tiên của giá trị gold theo P131/P361, và mọi cạnh trên đường đi hợp lệ tại thời điểm của fact (P131 là contemporary); v' là con cháu (cụ thể hơn) ⇒ `UNKNOWN` |
| predicate mismatch | `predicate_mismatch` | `IRRELEVANT` (v1; v0 ghi `COMPATIBLE`) | passage diễn đạt rõ property p' ≠ p của cùng subject; (p, p') không inverse, không subproperty; v' là giá trị KG của (s, p') |
| inverse | `inverse_relation` | `COMPATIBLE` | (p, p') được khai báo inverse (P1696, hoặc Q21510855 với P2306), và passage nêu (v, p', s) khớp gold |
| homonym | `homonym`, `entity_identity_mismatch` | `IRRELEVANT` | passage nói về QID khác có cùng label, text có mô tả phân biệt (type/description), subject của câu hỏi có QID với P31 không giao với P31 của QID kia; thiếu bất kỳ điều kiện nào ⇒ `UNKNOWN` |

Operator xuất cả candidate `UNKNOWN` (minh bạch). Config có `drop_unknown` để loại chúng khỏi pool.

### B.4 Metric conflict (đơn vị = query; câu hỏi có mẫu số 0 thì bỏ qua và báo số query dùng được)

Ký hiệu:
- R: ranking của method sau khi loại; X: tập candidate bị loại; R0: ranking **tham chiếu** chỉ theo relevance (cùng
  scorer, không xử lý conflict).
- A_q = {c : `decision` = COMPATIBLE và `reasons` ≠ ∅} (apparent-compatible).
- K_q = {c : COMPATIBLE} (mọi passage compatible, kể cả gold).
- N_q = {c : CONTRADICTING}.

| Metric | Định nghĩa |
|---|---|
| `fcfr_abs@k` | \|{c ∈ A_q : c ∉ top_k(R)}\| / \|A_q\| — bị nhiễu bởi relevance, chỉ báo cáo kèm |
| `fcfr_paired@k` (**chính**) | \|{c ∈ A_q ∩ top_k(R0) : c ∉ top_k(R)}\| / \|A_q ∩ top_k(R0)\| |
| `fcfr_filter` | \|A_q ∩ X\| / \|A_q\| (không phụ thuộc k) |
| `ger_abs@k`, `ger_paired@k` | như trên nhưng với N_q (tỷ lệ passage CONTRADICTING nằm ngoài top-k; cao là tốt) |
| `wfr_compat_v1` | EvoTrustRAG Eq. 8 [paper p.10]: trung bình theo q của 𝟙[G_keep ∩ X_q ≠ ∅], với G_keep = K_q (mọi COMPATIBLE) |
| `wfr_support_v1` | như trên, với G_keep = passage COMPATIBLE có `answer_support` yes/partial (chỉ định nghĩa khi có nhãn người) |
| `den:*` | denominator: tổng số passage của A_q, N_q, K_q và số nằm trong top-k của reference, kèm số câu hỏi đóng góp |

Mỗi metric có bản theo từng `reason`, bản macro theo query (chính) và bản micro theo passage (phụ).
Retrieval metric (2026-11-05):
- Bản full-list (`recall@k`, `ndcg@k`, `mrr`) chỉ được báo cáo khi relevance judgment phủ toàn bộ pool.
- Bản condensed (`*_cond`) bỏ passage chưa có judgment trước khi tính. Passage chưa chú thích **không** bị coi là
  non-relevant.
Retrieval/QA giữ nguyên: Recall@k, MRR, nDCG@k (relevance = `is_gold`), EM/F1 (SQuAD normalization, max theo
answers).

### B.5 Metric typing (cho method trả về decision, Phase C)

Tính trên candidate có nhãn gold khác `UNKNOWN` (`typing_report` trong `src/kgrerank/metrics/decision.py`):
- accuracy và macro-F1 trên {COMPATIBLE, CONTRADICTING, IRRELEVANT}. Macro-F1 chỉ lấy trung bình trên các class có
  mặt trong gold hoặc prediction (quy ước của scikit-learn; sửa 2026-11-05, trước đó class vắng mặt bị tính F1 = 0);
- coverage (tỷ lệ method trả một decision khác `UNKNOWN`) và selective accuracy;
- **failure rate**: call lỗi (parse_error, truncated, thinking_output, backend_error) **không** phải `UNKNOWN`.
  Nó được tính là sai trong accuracy và macro-F1, làm giảm coverage, và được báo cáo riêng theo status.
  Mọi tỷ lệ dùng chung một mẫu số `n_passages`;
- CI 95% bằng **cluster bootstrap theo câu hỏi**, vì các passage cùng câu hỏi không độc lập; báo cáo `n_passages`,
  `n_questions` và số passage bị loại vì gold là `UNKNOWN`;
- confusion matrix, breakdown theo reason.

### B.6 Thống kê

- **Bootstrap.** Percentile bootstrap theo query, có seed. B = 1.000 cho smoke, 10.000 cho kết quả (EvoTrustRAG dùng
  10.000 paired query-level resamples [paper p.5, p.10]).
- **So sánh hai hệ thống.** Paired bootstrap, resample cùng tập query cho cả hai hệ thống.
- **Hệ thống ngẫu nhiên** (random ranker, LLM sampling). Chạy S seed (mặc định 5) và báo cáo:
  - mean ± SD theo seed;
  - CI trên metric theo query đã lấy trung bình qua seed.
- **Kiểm định.** Exact McNemar cho outcome nhị phân theo cặp (WFR mỗi query, cho cả `wfr_compat_v1` và
  `wfr_support_v1`); Holm cho nhiều so sánh.
- **Đơn vị độc lập là câu hỏi.** Metric mức passage (typing) dùng cluster bootstrap theo câu hỏi. Mọi bảng ghi mẫu số
  và số câu hỏi đóng góp.
- **MDE.** MDE ≈ (z₁₋α/₂ + z_power) · SD_diff / √N. Tập main có N = 109 câu hỏi (400 passage), không phải 300 query
  như dự kiến ban đầu. Ngưỡng đề xuất sau pilot phải ≥ MDE và ≥ SD giữa các seed của baseline. Stratum nhỏ, ví dụ
  Complementary (44 passage từ 6 câu hỏi), chỉ là exploratory.
- **GER.** "GER giảm ≤ 2 điểm %" là một **non-inferiority margin**: cần cận dưới của CI một phía, và rất có thể
  thiếu power ở N ≈ 300. MDE sẽ cho biết.

### B.7 Dữ liệu cho Phase B

Mọi slice ≤ 200 ví dụ; tổng `data/` ≤ 50 MB; mỗi slice có manifest.

| Slice | Nguồn | Giới hạn / licence | Ghi chú |
|---|---|---|---|
| Wikidata reference slice | WDQS (selection) + `Special:EntityData` | ≤ 200 entity/property, mục tiêu < 10 MB; CC0 | manifest ghi endpoint, request chính xác, thời điểm, ID, URL, sha256, `lastrevid`, commit của script; không dùng Action API (bị 429), không broad SPARQL, không scrape HTML |
| Ragability | `ofai/RagabilityCorpus` qua HF datasets-server | ≤ 200 rows; **CC-BY-SA-4.0** | manifest ghi URL, revision, sha256, số rows, attribution; derived dataset công khai sau này phải theo share-alike |
| 2WikiMultiHopQA | `samples.json` trong fork Relink (500 ví dụ, sha256 `dde3427d…`) | ≤ 200; licence data **[UNVERIFIED]** (repo gốc Apache-2.0) | `kg_derived = true` |
| CONFLICTS | `conflicts.jsonl` trong fork (sha256 `14559d5c…`) | ≤ 200; nội dung là trang web bên thứ ba → chỉ dùng local | nhãn conflict ở **mức query** → `meta`; passage `UNKNOWN` |
| Fixture synthetic | viết tay trong `tests/fixtures/` | `"synthetic": true` | dùng cho test và `make smoke` |

### B.8 Tiêu chí hoàn thành Phase B (trạng thái 2026-11-04, chi tiết: `reports/03b_phaseB_harness.md`)

- [x] `pyproject.toml` pin `==`; `make install && make test` pass trên Python 3.11 (54 test); `make lint` sạch.
- [x] `make smoke` 0,4 s; output có nhãn "smoke test on toy data – not a result".
- [x] Schema v1 + validation có test: chặn gold-CONTRADICTING; **cùng reason, khác evidence ⇒ khác decision**.
- [x] Label protocol v0: 9 operator, mỗi operator có ca đủ evidence và ca thiếu evidence ⇒ `UNKNOWN`; tất định
  theo seed, không phụ thuộc thứ tự operator.
- [x] Rerankers: BM25 có giá trị tính tay; random tất định; oracle cho FCFR = 0 / 1 ở hai cực.
- [x] LLM: từ chối endpoint không-local; dừng **trước** cap; JSONL không chứa key; test không dùng network.
- [x] Metrics: test tính tay cho B.4–B.5; bootstrap tất định; McNemar, Holm, MDE có test.
- [x] Slices đúng giới hạn B.7, có manifest; `data/` ≈ 6,2 MB:
  - Wikidata: 200 ID, 1,06 MB;
  - Ragability: 53 dòng (toàn corpus);
  - 2Wiki: 200;
  - CONFLICTS: 200.
- [x] Không có code/data WikiRecentChanges (test `test_no_wikirecentchanges_material`).
- [x] `third_party/` và các fork không bị sửa; commit + push → **STOP POINT B**.
- [ ] **Chưa làm (cố ý):**
  - cross-encoder thật (không có GPU; extra `ce` chưa kiểm);
  - generator cho EM/F1;
  - ngưỡng mới (cần pilot trên MSI).
- [ ] **Cần bạn quyết trước Phase C:** tập chú thích mức passage độc lập với KG (FCFR không xác định trên dữ liệu
  tự nhiên, `03b` §5.1) — cỡ mẫu, nguồn, số annotator.

## Phase C — IDEA SKELETON (prototype, không phải kết quả)

### Thiết kế
- (Đã thực hiện bằng `kg/view.py` + `kg/settings.py` thay cho `TinyKG`; xem C.0 và tiêu chí bên dưới.)
- `kg/TinyKG` (từ fixture): entity type (P31-like), subclass (P279-like), located-in (P131-like),
  part-of (P361-like), alias kể cả historical name có thời gian hiệu lực (Saigon ↔ Ho Chi Minh City,
  Bombay ↔ Mumbai, Edo ↔ Tokyo), fact có qualifier start/end. API dự kiến: `resolve(name)`,
  `types(eid)`, `is_a(eid, cls)`, `located_in_ancestors(eid)`, `facts(s, p, at=None)`.
- `extract/`: `TripleExtractor` (`MockExtractor` pattern-based + `LLMExtractor` với prompt yêu cầu
  JSON, validate schema, dùng `LLMBackend`); `EntityLinker` dựa trên alias table, có ràng buộc type.
- `conflict/` (**G2⁺ skeleton**, cập nhật 2026-11-04 theo `02d`): tính **riêng** 6 signal (B.0 mục 4), mỗi signal
  có `basis`. Một **policy kết hợp tường minh, có version** sinh ra `decision` + `confidence` + evidence; thiếu
  evidence ⇒ `UNKNOWN` ⇒ **LLM fallback** (cascade KG-first). Constraint chỉ là soft evidence: không có rule
  "single-value ⇒ genuine"; không có `homonym → IRRELEVANT` cố định; không có thứ tự luật cứng.
- `conflict/ConflictAwareReranker`: `score = relevance − λ · penalty`; penalty **chỉ** khi `decision =
  CONTRADICTING` (tỷ lệ với `confidence`), kèm KG evidence làm lời giải thích. Báo cáo riêng theo setting KG
  S0–S3 (`02d` §5.4). Claim tham chiếu: (i) consensus của pool sau khi chuẩn hóa apparent conflict, hoặc (ii)
  fact trong KG (chỉ ở S3, là upper bound); giới hạn đã biết: consensus sai khi misinformation chiếm đa số.

### Deliverables
`src/kgrerank/{kg,extract,conflict}/`, unit test cho từng loại conflict, smoke test CPU,
`reports/04_ranked_recommendation.md`, `reports/05_pilot_plan.md` (pilot 300 câu trên RTX 5090 +
WSL2: venv, PyTorch build CUDA ≥ 12.8, kiểm `torch.cuda.get_device_capability() == (12, 0)`,
`vllm serve <model 7–8B instruct>`, `scripts/run_pilot.py`; phương án 32 GB và 24 GB),
`reports/06_compute_estimates.md`, `reports/07_uncertainties.md`, `HANDOFF.md`, Pull Request.

### C.0 Bổ sung theo quyết định của bạn (2026-11-04): tập chú thích độc lập

- **Tập chú thích:**
  - khoảng 400 item mức passage: CONFLICTS 300 (phân tầng theo category), 2Wiki 100;
  - pilot 40 item; tập double-annotate 120 item;
  - pre-register bằng seed cố định, commit `d197d5d` **trước** mọi code G2⁺.
- **Protocol:** `docs/ANNOTATION_GUIDELINES.md`. Codebook: `docs/annotation/codebook_v0.md` (nay là v0.1 draft cho
  pilot, xem C.1).
- **Tooling:** `scripts/annotation/` gồm sample, submit, agreement, adjudicate, export; package
  `src/kgrerank/annotation/`.
- **Vai trò:** đây là bằng chứng chính cho G7; synthetic chỉ là stress test.
- **Không nhìn trước:** annotator không thấy prediction, score hay quyết định KG.
- **Không có LLM gold.**

### C.1 Pre-pilot review (2026-11-05) — quyết định và sửa đổi trước khi chú thích

- **Question frame:** LLM parse + linking tự động (`src/kgrerank/frames/`). `InferenceFrame` không có `gold`.
  - `QuestionFrame` (có `gold`) chỉ dùng để xây synthetic.
  - Mơ hồ hoặc không tìm thấy → unresolved. Câu hỏi multi-hop/comparison → unsupported → fallback.
  - Thời gian tương đối chỉ giải theo snapshot benchmark.
  - Audit bằng người trên một mẫu riêng; human-framed diagnostic báo cáo riêng.
- **Policy G2⁺ v0.2** (`src/kgrerank/conflict/policy.py`), sửa **trước** khi có kết quả G2⁺ trên dữ liệu thật:
  - single-best-value không còn tạo conflict (nó cho phép nhiều giá trị);
  - không còn giả định hai phát biểu không ngày tháng là cùng thời điểm;
  - single-value có separator → unknown; constraint deprecated bị bỏ qua;
  - mention mơ hồ luôn → unknown (bỏ luật "mặc định entity của câu hỏi").
- **Đường LLM:**
  - extractor nhận câu hỏi thật;
  - prompt không còn hỏi về "other evidence" khi không cung cấp nó. Hai baseline có information access rõ:
    `single_passage_v1` và `inter_context_v1`. Fallback của G2⁺ dùng cùng prompt `inter_context_v1`;
  - output JSON, `max_tokens` mặc định 256. Trạng thái ok / parse_error / truncated / thinking_output /
    backend_error được tách khỏi UNKNOWN hợp lệ.
- **Accounting:**
  - `llm_calls` gồm mọi vai trò: frame_parse, extract, fallback, judge;
  - kèm token ước tính, latency và số lỗi; cache policy = none.
- **Thống kê:** typing metric dùng cluster bootstrap theo câu hỏi.
- **Model MSI:** `Qwen/Qwen3-8B`, revision `b968826d…`, BF16, non-thinking (`configs/msi/qwen3_8b.yaml`).
- **Trình tự đánh giá** (khóa; `docs/ANNOTATION_GUIDELINES.md` §12):
  1. sửa protocol;
  2. pilot 40 item;
  3. freeze codebook v1;
  4. engineering pilot trên MSI, chỉ trên tập pilot (12 câu hỏi, không trùng 109 câu của main);
  5. main annotation và evaluation.

  Main set không dùng để chọn prompt, policy, λ hay threshold.

### Tiêu chí hoàn thành Phase C (trạng thái 2026-11-04; cập nhật vòng review 2026-11-05 ở C.2)

- [x] Fixture KG hư cấu `tests/fixtures/toy_kg.json`:
  - chuỗi located-in 3 cấp; fact có start/end (P6); cặp homonym khác P31 **và** cặp homonym cùng P31;
  - predicate liên quan (P19/P20); inverse (P22/P40); historical name có thời gian (P1448).
  - Chỉ có **1** alias + 1 historical name, không đủ "≥ 3 alias" như kế hoạch. Alias thật có nhiều trong Wikidata
    slice (Saigon, Bombay, Madras, Leningrad).
- [x] Unit test G2⁺: mỗi reason type có ca positive, near-miss và ca thiếu evidence ⇒ `UNKNOWN`
  (`tests/test_g2plus.py`). Policy có version (`policy_v0.1`, nay là `policy_v0.2`, xem C.1) và mỗi quyết định
  ghi rule đã kích hoạt.
- [x] Smoke: BM25 vs ConflictAwareReranker (S0, S2, S3, filter) trên fixture, có nhãn
  "smoke test on toy data – not a result".
- [x] `04` xếp hạng; `05` lệnh **[UNVERIFIED — chưa chạy trên phần cứng đích]** cho 32 GB/24 GB; `06` ước tính theo
  công thức; `07` gom mọi [UNVERIFIED].
- [x] `HANDOFF.md`.
- [x] Annotation: protocol, codebook v0, schema + JSON Schema, template, sampling deterministic + manifest, agreement
  (kappa, alpha với MASI), adjudication (giữ nhãn trước adjudication), export; dry-run end-to-end trên bản sao rồi
  xóa.
- [ ] **Chưa làm (cần người hoặc GPU):**
  - chú thích pilot và main;
  - question frame cho dữ liệu tự nhiên;
  - baseline LLM thật;
  - literature search có hệ thống.
- [x] Mở Pull Request `claude/paper3-audit-20261102` → `main`
  ([Thuy-g/paper3-kg-conflict-rerank#1](https://github.com/Thuy-g/paper3-kg-conflict-rerank/pull/1)) → **DỪNG**.

### C.2 Tiêu chí hoàn thành vòng pre-pilot review (2026-11-05)

- [x] Mọi nhận xét kỹ thuật của bạn được kiểm trong code (`reports/08_prepilot_review.md` §1). Không có nhận xét nào sai.
- [x] Question frame: package `frames/`, prompt chỉ nhận câu hỏi, linking giữ trạng thái unresolved, coverage, audit
  tooling (`scripts/frames/`), test `tests/test_frames.py`.
- [x] Policy v0.2 (SBV, thời gian, separator, exception, deprecated, mention mơ hồ), test `tests/test_g2plus.py`.
- [x] Đường LLM: question vào extractor, hai baseline có information access rõ, trạng thái lỗi tách khỏi `UNKNOWN`,
  accounting đủ vai trò; test `tests/test_llm_path.py`.
- [x] Metric: hai biến thể WFR có tên, condensed retrieval metric, denominator, cluster bootstrap, export 2Wiki tách
  supporting facts khỏi nhãn người; test `tests/test_eval_accounting.py`.
- [x] Codebook v0.1 (draft), CHANGELOG, `A2_quickstart.md` (A2: TBD); sample v1 và manifest giữ nguyên.
- [x] Config MSI cho `Qwen/Qwen3-8B` (revision và hash pin; lệnh server **[UNVERIFIED trên phần cứng đích]**).
  Config tách theo bước: `frames_pilot_qwen3.yaml` và `engineering_pilot.yaml` (tập pilot, bước 4);
  `frames_v1_qwen3.yaml` và `main_eval.example.yaml` (main, bước 5).
- [x] Offline checks: `make lint`, `make test`, `make smoke`.
- [ ] **Cần người hoặc MSI:** pilot 40 item với A1/A2; engineering pilot trên MSI; frame audit; xác nhận snapshot
  CONFLICTS.

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
| Circularity: nhãn synthetic sinh từ Wikidata, method cũng dùng Wikidata | synthetic chỉ là capability probe; setting S0–S3 + masking; tập nhãn độc lập với KG (`02d` §5.4) |
| Answer leakage: 2Wiki/ConflictBank/TimeQuestions xây từ Wikidata | cờ `meta.kg_derived`; báo cáo tách; S3 chỉ là upper bound |
| WDQS là live, có lag | WDQS chỉ để selection; statement lấy từ `Special:EntityData` + `lastrevid`; dump có ngày cố định trên MSI |
| Ngưỡng H-G2/H-G7 chưa có cơ sở | đo variance/effect size/CI/MDE trong pilot rồi mới đề xuất; pre-register trước khi chạy G2⁺ |
| Ragability là CC-BY-SA-4.0 | raw chỉ trong `data/`; derived dataset công khai phải share-alike + attribution |

## Ước tính chi phí
- Phase A: chỉ đọc code + script nhỏ; CPU không đáng kể; không tải dữ liệu.
- Phase B: cài package (vài phút); tiny slice vài MB. Nếu làm `CrossEncoderReranker` thật sẽ cần
  `torch` bản CPU + `sentence-transformers` + model MiniLM-L6 — dung lượng sẽ được kiểm trước khi
  tải; nếu bước nào dự kiến > 5 phút CPU sẽ dừng hỏi bạn.
- Phase C: CPU không đáng kể; không gọi API trả phí.
