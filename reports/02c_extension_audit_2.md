# 02c — Audit mở rộng đợt 3: When Facts Change, Ragability (+ llms-wrapper), TimeR4, PAGE-RAG — và gợi ý sơ bộ cập nhật

> Yêu cầu: audit code của 5 repo, đọc 3 PDF mới (When Facts Change, Ragability, TimeR4; PAGE-RAG đã có PDF từ trước), trả lời câu hỏi
> mở rộng thành bài journal OA, và cập nhật gợi ý sơ bộ. Audit chỉ đọc. Ký hiệu nguồn như `02`/`02b`:
> **[code]**, **[paper tr. X]**, **[data]**, **[UNVERIFIED]**.

## 1. Clone, commit, và một lỗi quy trình

| Repo | Upstream | Exit | HEAD (upstream = fork `Thuy-g/*`) | Commit cuối | Kích thước |
|---|---|---|---|---|---|
| knowledge-conflicts-mutability | github.com/jwallat/knowledge-conflicts-mutability | 0 | `a3f62cf33b0c85f8fb110a5daa276399f50e63b6` ✅ | 2026-04-15, Jonas Wallat, "initial commit" | 15 MB |
| python-ragability | github.com/OFAI/python-ragability | 0 | `ff15ca3cd3dcf6b4802a7a6fcc2c67057878c56f` ✅ | 2025-08-20, Brigitte Krenn | 0,8 MB |
| python-llms-wrapper | github.com/OFAI/python-llms-wrapper | 0 | `093f61e87bde50e2f95c6589af77b2d07c0d6e38` ✅ | 2026-08-19, Johann Petrak | 2,2 MB |
| TimeR4 | github.com/qianxinying/TimeR4 | 0 | `508cc0267e55f24877b136f23f0f3c425f2d37b4` ✅ | 2025-11-15, qianxinying | **858 MB** |
| PAGE-RAG | github.com/CXY0112/PAGE-RAG | 0 | `30f6eb28e3ff789256fdb487372827c82b8400c3` ✅ | 2026-07-22, Starry | 4 MB |

**Lỗi quy trình:** tôi đã clone TimeR4 mà **không kiểm dung lượng trước**. 858 MB gồm dataset MultiTQ/TimeQuestions và file kết quả đi kèm repo
(file lớn nhất là `datasets/MultiTQ/prompt/train_prompt.json`, 81,8 MB). Đã kiểm: **không có model weights** (không có `.bin/.safetensors/.pt/.ckpt/.gguf`),
nhưng việc này vẫn đi ngược tinh thần quy tắc "tiny data". Cách làm đúng từ nay (đã ghi vào `CLAUDE.md`):
`git clone --depth 1 --filter=blob:none --no-checkout <url>` → `git ls-tree -r -l HEAD | sort -k4 -n` để xem dung lượng từng file → `git sparse-checkout`
chỉ lấy phần code. `third_party/` không được commit.

## 2. License và hệ quả

| Repo | License | Hệ quả |
|---|---|---|
| knowledge-conflicts-mutability | **Không có LICENSE** | Không copy code hay dữ liệu WikiRecentChanges vào sản phẩm; cần xin phép, hoặc tự dựng lại từ Wikidata (CC0) bằng script của mình. Danh sách property mutable/stable là **dữ kiện** có thể trích dẫn. |
| python-ragability | Apache-2.0 | Dùng được. Corpus nằm trên HF tại `ofai/RagabilityCorpus`, tag **`license:cc-by-sa-4.0`** (đọc qua HF API) → dùng được, bắt buộc ghi nguồn, và dữ liệu dẫn xuất phải theo **share-alike**. |
| python-llms-wrapper | Apache-2.0 | Dùng được (LiteLLM). |
| TimeR4 | **Không có LICENSE** | Cài lại từ paper (công thức fused score và quy tắc sắp theo thời gian rất ngắn). Weights để trên Baidu Pan (`baidu` — `third_party/TimeR4/README.md:25`), khả năng truy cập: **[UNVERIFIED]**. |
| PAGE-RAG | Apache-2.0 | Dùng được. |

## 3. Bản đồ code

Nhóm: DL = data loading, RET = retrieval, KG = KG construction & triple extraction, CF = conflict detection & filtering, LLM = backend, EV = evaluation.

### 3.1 When Facts Change (`knowledge-conflicts-mutability`) — 19 file `.py`, 4.466 LOC

| Nhóm | Symbol — vị trí | Ghi chú |
|---|---|---|
| DL | dữ liệu [data] | `mutable_final.csv` 2.330 dòng, `stable_final.csv` 2.381 dòng; tập 1k và `yearshift/` (dời năm +0/+1/+5/+10). Cột: Question, Answer, Counterfactual fact, Context, Counterfactual Context. **Một context mỗi câu.** |
| KG | `MUTABLE_PROPERTIES` — `third_party/knowledge-conflicts-mutability/data/recent_changes/ds_creation/extract_triples_from_dump.py:13-39` | Property **mutable** của Wikidata: P39 position held, P54 member of sports team, P108 employer, P159 headquarters location, P551 residence, P463 member of… |
| KG | `STABLE_PROPERTIES` — `third_party/knowledge-conflicts-mutability/data/recent_changes/ds_creation/extract_stable_entities.py:17-44` | Property **stable**: P19 place of birth, P20 place of death, P27 country of citizenship, P569/P570 date of birth/death, P22/P25 father/mother, P21… |
| KG | `TIME_QUALIFIERS` — `third_party/knowledge-conflicts-mutability/data/recent_changes/ds_creation/extract_triples_from_dump.py:10` | P580 start, P582 end, P585 point in time → **kiểm chứng** được các mã qualifier mà `CLAUDE.md` dùng. |
| KG | `hf_pipe` — `third_party/knowledge-conflicts-mutability/generate_counterfactual_paragraphs.py:39` | Context counterfactual sinh bằng **Gemma-3-12B** (HF local). |
| RET | không có | Context được cho sẵn. |
| CF | không có bộ lọc | Đây là nghiên cứu hành vi model; có các biến thể prompt (nudge, ngày tài liệu). |
| LLM | `model_cutoffs` — `third_party/knowledge-conflicts-mutability/run_conflict_qa.py:33` | Model HF local (Gemma-3, Phi-4, gpt-oss-20b/120b, Qwen3-8B, Olmo-3, Llama-3.3-70B, R1-Distill); `context_type` true/counter ở dòng 65–70. |
| EV | `compute_contains_metric` — `third_party/knowledge-conflicts-mutability/src/evaluation.py:94` | Ngoài ra có BEM: `compute_bemscore` — `third_party/knowledge-conflicts-mutability/src/bem.py:46`. Thư mục `predictions/` mà README nhắc tới **không có trong repo**. |

### 3.2 Ragability (`python-ragability` + `python-llms-wrapper`) — 17 + 13 file `.py`

| Nhóm | Symbol — vị trí | Ghi chú |
|---|---|---|
| DL | `read_input_file` — `third_party/python-ragability/ragability/data.py:76` | Đọc corpus định dạng hjson/tsv. Corpus **không có trong repo** (dù docs ghi là có: `ragability` — `third_party/python-ragability/docs/index.md:37`); phát hành trên HF (`ofai/RagabilityCorpus`). |
| DL | `row2raga_ctx1234qh` — `third_party/python-ragability/ragability/ragability_cc_wc1.py:255` | Sinh tổ hợp context (1–4, đổi thứ tự) × query × **có hoặc không gợi ý ("hint")** từ WikiContradict. |
| RET / KG | không có | — |
| CF | không có detector | Benchmark: hỏi model "có mâu thuẫn không" (yes/no) và hỏi nội dung. |
| LLM | `LLMS` — `third_party/python-llms-wrapper/llms_wrapper/llms.py:312` | LiteLLM; `api_base` lấy từ config (`api_base` — `third_party/python-llms-wrapper/llms_wrapper/llms.py:826`) → trỏ sang vLLM được (**[UNVERIFIED]**, chưa chạy). |
| EV | `affirmative` — `third_party/python-ragability/ragability/checks.py:76` | Các check: `is_eq`, `contains`, `negative`, `unknown`…; tổng hợp ở `run` — `third_party/python-ragability/ragability/ragability_eval.py:88`. |

### 3.3 TimeR4 — 19 file `.py`, 1.756 LOC

| Nhóm | Symbol — vị trí | Ghi chú |
|---|---|---|
| DL | dữ liệu [data] | MultiTQ, TimeQuestions (KG `full.txt` + câu hỏi) kèm trong repo. |
| RET | `NegativeSampler` — `third_party/TimeR4/construct_negatives.py:10` | Sinh negative có tính thời gian cho contrastive retriever. |
| RET | `re_rank_single_result` — `third_party/TimeR4/retrival.py:194` | Rerank: `final_score` = α·sim + (1−α)·time_match (`final_score` — `third_party/TimeR4/retrival.py:264`); câu "first/last" thì sắp theo thời gian (`with_time` — `third_party/TimeR4/retrival.py:281`). |
| KG | không dựng KG | Dùng TKG có sẵn (quadruple). |
| CF | không có | TKG được coi là đúng; không có khái niệm conflict. |
| LLM | `gpt_chat_completion` — `third_party/TimeR4/main.py:109` | Bước **rewrite** câu hỏi gọi `gpt-3.5-turbo-0125` (**API trả phí**); bước suy luận dùng LLaMA2-7B fine-tune (`train` — `third_party/TimeR4/train.py:161`). |
| EV | `eval_hit` — `third_party/TimeR4/predict_answer.py:41` | Hits@k. |

Nhóm tác giả đã có bài tiếp nối: `Plan` — `third_party/TimeR4/README.md:8` ("Plan of Knowledge", arXiv 2511.04072).

### 3.4 PAGE-RAG — 79 file `.py`, 7.971 LOC

| Nhóm | Symbol — vị trí | Ghi chú |
|---|---|---|
| DL | `scripts/build.py` (EPUB → chunk) | Corpus dạng sách; cần Neo4j 5.x. |
| KG | `RELATION_CONSTRAINTS` — `third_party/PAGE-RAG/src/algorithm/construction/graph_validation.py:32-46` | **Ràng buộc domain/range** cho từng relation (ví dụ LOCATED_IN: placeable → PLACE); cạnh vi phạm bị hạ xuống RELATED_TO (`relation_domain_range` — `third_party/PAGE-RAG/src/algorithm/construction/graph_validation.py:157`). |
| KG | `MergeCandidate` — `third_party/PAGE-RAG/src/algorithm/construction/entity_alignment.py:1-8` | Chỉ tự gộp khi **cùng type + tên chuẩn hóa trùng hệt**; alias trùng tên chuẩn của entity khác thì bị xóa (`AliasConflict` — `third_party/PAGE-RAG/src/algorithm/construction/entity_alignment.py:68`) — một dạng **bảo vệ homonym** (ví dụ cha và con trùng tên). |
| RET | `ground_evidence` — `third_party/PAGE-RAG/src/algorithm/query/evidence_grounding.py:26` | Định tuyến truy vấn: text floor + graph operator. |
| CF | không có typing conflict | — |
| LLM | `base_url` — `third_party/PAGE-RAG/src/infrastructure/llm/registry.py:32` | Endpoint OpenAI-compatible → vLLM được. |
| EV | `sufficient` — `third_party/PAGE-RAG/src/algorithm/query/answer_generation.py:66` | Answer-or-refuse: thiếu evidence thì đặt `sufficient=false`. |

## 4. Paper: các điểm chính (có trang)

- **When Facts Change** (Wallat, Sikdar, Nejdl — L3S; Findings of ACL 2026, pp. 2154–2184):
  - LLM **có nói ra** suy luận về mutability với fact đã thay đổi, nhưng điều đó **hiếm khi ảnh hưởng tới câu trả lời cuối**; nhắc model xét mutability làm tăng việc nhắc tới thay đổi theo thời gian nhưng **không tăng độ chính xác** [tr. 1, 9].
  - Model nhỏ hiếm khi phát hiện ra conflict; model lớn phát hiện được nhưng không hành động theo phán đoán mutability [tr. 1, 9].
  - Steering theo hướng tin context giả định context đáng tin hơn — giả định này sai trong thực tế [tr. 9].
  - **Giới hạn tự nêu**: chỉ xét conflict context–parameter với **một** context; "inter-context conflicts will be more realistic, but was out of scope" [tr. 10].
- **Ragability** (Gross, Petrak, Krenn — OFAI; LREC 2026):
  - Lấy 92 instance "implicit reasoning" của WikiContradict → 51 cặp phân biệt → bỏ 8 [tr. 3]; thay entity thật bằng **entity hư cấu** để loại ảnh hưởng của parametric knowledge [tr. 1–3].
  - Model nhận ra mâu thuẫn tốt (yes/no) nhưng trả lời câu hỏi nội dung kém; **gợi ý "có thể có mâu thuẫn" làm tăng detection trên context mâu thuẫn nhưng làm giảm đáng kể kết quả trên context không mâu thuẫn**, tức là gây false alarm [tr. 1].
  - Đánh giá 7 LLM, trong đó 6 là model proprietary [tr. 7].
- **TimeR4** (Qian et al. — Nankai; EMNLP 2024):
  - Retrieve-rewrite-retrieve-rerank cho TKGQA; retriever contrastive theo thời gian; µ = 0,4 [tr. 1–6].
  - Rewrite bằng gpt-3.5-turbo; fine-tune LLaMA2-Chat-7B trên 2× A6000 [tr. 6]; cải thiện tương đối 47,8% và 22,5% [tr. 1].
- **PAGE-RAG** (Chen et al. — CUIT, Beihang; arXiv 2607.19301):
  - Projection-aware repository + routing + answer-or-refuse; từ chối đúng 24/24 câu không trả lời được, bỏ ràng buộc evidence thì còn 4/24 [tr. 4].
  - Đánh giá trên 2 sách tiếng Anh + 1 benchmark sensemaking [tr. 12].

## 5. (f) Mở rộng từng bài thành bài journal Open Access?

Tiêu chí venue như `02b` §6.1. Không có gì bảo đảm accept.

| Bài | Phán đoán | Hướng mở rộng cụ thể | Khớp Paper 3 | Rủi ro chính |
|---|---|---|---|---|
| **When Facts Change** | **Có, có điều kiện — khớp nhất trong đợt này** | Đưa sang **inter-context** (chính hướng tác giả bỏ ngỏ [tr. 10]): pool có passage đúng, **outdated** và **counterfactual** cho fact mutable và stable; đưa **mutability thành tín hiệu tường minh lấy từ KG**, dùng trong typer/reranker thay vì trông chờ LLM tự áp dụng (vì paper cho thấy LLM không làm được [tr. 9]) | **rất cao** (đúng ranh giới temporal_scope vs genuine) | Không có license (phải tự dựng dữ liệu từ Wikidata hoặc xin phép); Wikidata bị chặn ở cloud |
| **Ragability** | Có, có điều kiện | (a) Mở rộng corpus bằng **instance có apparent conflict** (alias, granularity, temporal) làm control "không mâu thuẫn", giữ thủ thuật entity hư cấu; (b) dùng làm **bộ đo false alarm** (hiệu ứng hint) cho G7 | cao (cho phần đánh giá) | Corpus nhỏ; tự nó là benchmark nên phần thuật toán mỏng; CC-BY-SA kéo theo share-alike |
| **TimeR4** | Có, có điều kiện | Chuyển rerank theo ràng buộc thời gian từ fact TKG sang **passage văn bản có xung đột**, kết hợp với mutability; hoặc đưa conflict vào TKGQA | trung bình (trục thời gian) | Không có license; cần fine-tune (LoRA trên 32 GB: **[UNVERIFIED]**); rewrite dùng API trả phí; nhóm tác giả đang phát triển tiếp (Plan of Knowledge) |
| **PAGE-RAG** | Có, có điều kiện, **ưu tiên thấp** | Answer-or-refuse **có xét conflict**: conflict genuine chưa giải quyết được thì abstain hoặc hedge; dùng domain/range + type cho homonym | thấp–trung bình | Bài toán khác (sách dài, không phải fixed pool); đánh giá nhỏ; cần Neo4j |

## 6. Bảng tổng hợp khả năng mở rộng (mọi công trình đã audit)

Xếp theo mức khớp với Paper 3 (fixed-pool, KG-guided, apparent vs. genuine). "OA venue" là venue hợp nhất theo tiêu chí ở `02b` §6.1.

| Công trình | Code / license | Ý tưởng mở rộng tốt nhất | Khớp | Novelty risk | OA venue |
|---|---|---|---|---|---|
| MemGraphRAG (KDD'26) | có / MIT | KG-schema thay cho phán đoán LLM trong typing; đo detector; dùng lúc truy vấn | rất cao | trung bình–cao | IEEE Access |
| When Facts Change (Findings ACL'26) | có / **không license** | Mutability tường minh cho inter-context pool | rất cao | trung bình | IEEE Access / PLOS ONE |
| Decision-model typing (arXiv'26) | có / Apache-2.0 | Cascade KG-first + typer open-weight, typing mức passage | cao | trung bình–cao | PLOS ONE / Sci Rep |
| Ragability (LREC'26) | có / Apache-2.0 + CC-BY-SA | Control apparent conflict + đo false alarm | cao (đánh giá) | trung bình | PLOS ONE / Sci Rep |
| ArbGraph (arXiv'26) | có / **không license** | Typed arbitration (chỉ phân xử genuine) | cao | trung bình | IEEE Access |
| EvoTrustRAG (arXiv'26) | **không có code** | (dùng WFR làm metric đối chiếu) | trung bình | — | — |
| TruthfulRAG (AAAI'26) | có / Apache-2.0 | Baseline filter; chỉ ra giả định tin context | trung bình | — | — |
| TimeR4 (EMNLP'24) | có / **không license** | Rerank thời gian cho passage có conflict | trung bình | trung bình | IEEE Access |
| ContextConflict (EMNLP'26) | có (thiếu code steering) / **không license** | Steering trên pool thật | thấp | trung bình | Sci Rep / PLOS ONE |
| ProStruct-RAG (EMNLP'26) | có / Apache-2.0 | Baseline typing theo thời gian (updates/contradicts) | trung bình | — | — |
| PAGE-RAG (arXiv'26) | có / Apache-2.0 | Abstain khi có conflict genuine chưa giải quyết | thấp–trung bình | thấp | IEEE Access |
| MAGIC, CONFLICTS, GraphRAG-Bench, Relink | có | Dữ liệu / evaluator / ý tưởng predicate-distractor | (hỗ trợ) | — | — |

## 7. Gợi ý sơ bộ cập nhật (thay cho "G7 → G2+G1")

### 7.1 Điều gì đã thay đổi kể từ gợi ý trước

1. **Taxonomy không còn mới**: MemGraphRAG/HVM đã có mutual/temporal/granularity bằng prompt LLM (`02b`).
2. **Mutability là bản lề còn bỏ ngỏ**: When Facts Change cho thấy LLM **biết nhưng không dùng** mutability [tr. 9], và tự nhận chưa xét inter-context [tr. 10].
   MemGraphRAG cũng bắt LLM tự phán "predicate uniqueness" (`02b` §4.3), tức là cùng điểm yếu đó.
3. **False alarm đã được ghi nhận nhưng chưa được đo đúng chỗ**: Ragability (hint làm tăng false alarm trên context không mâu thuẫn), MAGIC (over-detection),
   EvoTrustRAG (WFR mức query), ConflictRAG (giả thuyết Self-RAG lọc quá tay). **Chưa thấy** phép đo mức passage theo từng loại apparent.
4. **G1 (KG-consistency) yếu**: novelty thấp và có rủi ro rò rỉ đáp án (2Wiki dựng từ Wikidata).
5. **Schema constraint mới chỉ được dùng để "làm sạch graph"** (domain/range và bảo vệ alias của PAGE-RAG), chưa được dùng để **quyết định loại conflict** khi rerank.

### 7.2 Gợi ý hiện tại: **G7 → G2⁺ (schema + mutability)**, G3 đưa vào lõi, G1 chỉ còn là ablation, G8 để bài sau

Tên làm việc: *"Mutability- and Schema-Aware Conflict Typing for Evidence Reranking in RAG"* (hoặc giữ tiêu đề "Relation-Aware…").

1. **Phần động lực (G7)**: đo **FCFR@k / GER@k** (mức passage, theo loại) và **WFR** (mức query, định nghĩa của EvoTrustRAG) cho các bộ xử lý conflict đại diện:
   prompt typer của MemGraphRAG (MIT), prompt của CONFLICTS (Apache, qua repo Khatri), relation extractor của ProStruct (Apache), verifier + trọng tài
   kiểu ArbGraph (cài lại), entropy filter của TruthfulRAG (Apache), có và không có "hint" (theo Ragability).
   Giả thuyết: các bộ này gán nhầm genuine cho apparent conflict, nặng nhất ở **temporal trên fact mutable** và ở **granularity/alias**.
2. **Phương pháp (G2⁺)**: typer **KG-first** dùng 6 tín hiệu schema kiểm chứng được:
   (i) **mutability/uniqueness của property** (stable/mutable; ràng buộc single-value của Wikidata: **[UNVERIFIED]** cách lấy);
   (ii) **qualifier thời gian** P580/P582/P585 (đã kiểm qua code của When Facts Change);
   (iii) hierarchy P131/P361; (iv) **alias có thời gian hiệu lực**; (v) **type P31** cho homonym; (vi) bản đồ predicate liên quan.
   LLM (prompt MemGraphRAG) chỉ là fallback khi KG không phủ. Reranker chỉ phạt `genuine`, kèm KG facts làm lời giải thích; tùy chọn **abstain**
   với conflict genuine chưa giải quyết được (ý tưởng của PAGE-RAG).
3. **Dữ liệu** (tiny slice ở Phase B, đầy đủ ở pilot): 2Wiki (Relink) + perturbation có kiểm soát; CONFLICTS (pool tự nhiên); MAGIC (genuine);
   Ragability (CC-BY-SA; control không mâu thuẫn); fact mutable/stable **tự dựng từ Wikidata** trên máy local (thay cho WikiRecentChanges vì thiếu license);
   ContextConflict nếu xin được phép.
4. **Tiêu chí bác bỏ (đề xuất, cần bạn chốt)**: KG-first typer phải giảm FCFR@5 ít nhất 10 điểm % so với typer LLM tốt nhất, với GER@5 không tụt quá
   2 điểm % và số lần gọi LLM ít hơn ít nhất 50%. Nếu không đạt thì chuyển sang **phương án dự phòng**: công bố phần (1) như một nghiên cứu thực nghiệm
   (PLOS ONE / Sci Rep).
5. **Venue**: IEEE Access nếu (2) đạt tiêu chí; PLOS ONE / Sci Rep nếu chỉ có (1) vững.

### 7.3 Vì sao tốt hơn gợi ý cũ

- Điểm mới dựa vào chỗ **có bằng chứng là còn trống**: mutability chưa được dùng như tín hiệu tường minh (When Facts Change), detector chưa được đo
  (MemGraphRAG/HVM), và false alarm chưa được đo ở mức passage. Ta **không** cạnh tranh trên taxonomy.
- Phần đánh giá dùng nhiều dữ liệu và baseline có **license cho phép** (MIT, Apache, CC-BY, CC-BY-SA), giảm rủi ro pháp lý.
- Khả thi trên 1× RTX 5090: phần typing chạy CPU; LLM 7–8B chỉ dùng làm baseline và fallback.

### 7.4 Rủi ro còn lại

- Nhóm XMU/JLU (MemGraphRAG, HVM) có thể ra phiên bản query-time hoặc dựa trên schema trước ta.
- Cần **Wikidata trên máy local** (dump hoặc SPARQL), dung lượng phải ước tính ở Phase C.
- Ngoài phạm vi những gì đã audit có thể có công trình trùng: **[UNVERIFIED]**, cần một lượt tìm có hệ thống trước khi viết.
- Các bộ dữ liệu nhỏ (CONFLICTS 406 test, Ragability khoảng 43 instance) → cần sinh dữ liệu có kiểm soát và bootstrap CI.

### 7.5 Ảnh hưởng tới Phase B (nếu bạn đồng ý)

- `TinyKG` fixture thêm cờ **mutable/stable** và **single-value** cho từng property, qualifier P580/P582/P585, alias có `valid_from`/`valid_to`.
- `perturb/` thêm phân biệt **temporal trên property mutable** (apparent) và **giá trị khác trên property stable** (genuine).
- Metric thêm **WFR** bên cạnh FCFR/GER.
- Slice: 2Wiki (Relink), CONFLICTS (local), MAGIC (local), Ragability (tải ≤ 200 dòng từ HF, CC-BY-SA, **cần bạn đồng ý tải**).

## 8. [UNVERIFIED] và việc cần làm phát sinh

1. Cách lấy danh sách property có ràng buộc single-value từ Wikidata (P2302 + Q19474404 — mã cụ thể **[UNVERIFIED]**), làm trên máy local.
2. Khả năng truy cập Baidu Pan (weights của TimeR4) và việc LoRA fine-tune 7B trên 32 GB.
3. vLLM có dùng được qua LiteLLM (`api_base`) cho Ragability không.
4. Xin phép tác giả When Facts Change về dữ liệu WikiRecentChanges, hoặc tự dựng lại.
5. Lượt tìm novelty có hệ thống (arXiv qua `curl`) cho cụm "mutability + inter-context conflict + reranking" trước khi viết paper.
