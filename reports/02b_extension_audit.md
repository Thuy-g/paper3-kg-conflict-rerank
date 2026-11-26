# 02b — Audit mở rộng: ContextConflict, decision-model conflict typing, MemGraphRAG (+ kiểm chứng 5 paper mới)

> Yêu cầu sau STOP POINT A: audit thêm 3 repo; đọc 5 PDF bạn attach (CONFLICTS, ConflictRAG, HVM-GraphRAG, MemGraphRAG,
> EvoTrustRAG); trả lời câu hỏi có mở rộng được thành bài journal Open Access hay không. Audit chỉ đọc.
> Ký hiệu nguồn giống `02_codebase_map.md`: **[code]**, **[paper tr. X]** (số trang của file PDF), **[data]** (đếm bằng script),
> **[UNVERIFIED]**.

## 1. Truy cập arXiv (sau khi bạn đổi network settings)

| Cách truy cập | Kết quả |
|---|---|
| `curl https://arxiv.org/abs/2606.00610` | **200**, tiêu đề đúng "MemGraphRAG: Memory-based Multi-Agent System for Graph Retrieval-Augmented Generation" |
| `curl https://arxiv.org/pdf/2606.00610` | **200** |
| `curl https://export.arxiv.org/...` | CONNECT 403 (host khác, không cần dùng) |
| Tool WebFetch tới `arxiv.org` | vẫn lỗi `getaddrinfo ENOTFOUND arxiv.org` (cơ chế phân giải tên của tool này khác sandbox; nguyên nhân **[UNVERIFIED]**) |

Kết luận: **đọc được arXiv bằng `curl` từ sandbox**. Cho phần audit này không cần tải thêm paper nào, vì bạn đã attach đủ.

## 2. Clone upstream và commit

Lệnh `git clone --depth 1 <upstream> third_party/<Repo>`; log nằm ở `reports/appendix/A_clone_attempts.log`. Hash của fork được lấy bằng `git ls-remote`.

| Repo | Upstream | Exit | HEAD (upstream = fork `Thuy-g/*`) | Commit cuối |
|---|---|---|---|---|
| context_conflict_emnlp_2026 | github.com/lei-nlp-lab/context_conflict_emnlp_2026 | 0 | `a44dad92e120a4f9415a76bc7d7891d50d7b0a1f` ✅ | 2026-09-17, Xinye Yang, "Revise README" |
| decision-models-conflict-typing | github.com/Parv17k/decision-models-conflict-typing | 0 | `fb55d742f0c650162dd0bfa38c694d101118b727` ✅ | 2026-10-29, Parv Khatri, "Add CITATION.cff for the arXiv paper" |
| MemGraphRAG | github.com/XMUDeepLIT/MemGraphRAG | 0 | `cd6fabda1ec31a302bb283089e17c087ab7713e8` ✅ | 2026-06-21, wuchuanjie, "update readme" |

Kích thước: 49 MB, 39 MB, 78 MB (phần lớn là dữ liệu và output đi kèm repo; `third_party/` không được commit).

## 3. License và hệ quả khi reuse

| Repo | License | Hệ quả |
|---|---|---|
| context_conflict_emnlp_2026 | **Không có file LICENSE**; dataset card trên HF (`AsherYang/ContextConflict`) cũng **không khai báo license** (API trả `license: None`) | Mặc định all rights reserved: được đọc và trích dẫn; **dùng dữ liệu trong bài journal cần hỏi tác giả**, và không nên phát hành lại dữ liệu đã dẫn xuất. Một phần nguồn là bài báo AllSides do nhóm tác giả tự thu thập [paper tr. 14]. |
| decision-models-conflict-typing | **Apache-2.0** (code, prompt, toàn bộ output) | Dùng và sửa thoải mái, giữ license + ghi thay đổi. Dữ liệu CONFLICTS giữ license riêng (Apache-2.0, © Google — theo README của repo). |
| MemGraphRAG | **MIT**, "Copyright (c) 2026 DeepLIT Group in Xiamen University" | Rất thoáng. README ghi "builds upon … HippoRAG" (`HippoRAG` — `third_party/MemGraphRAG/README.md:193`), nên license của phần kế thừa từ HippoRAG cần kiểm khi tái phân phối: **[UNVERIFIED]**. |

## 4. Bản đồ code

Quy ước nhóm: DL = data loading, RET = retrieval, KG = KG construction & triple extraction, CF = conflict detection & filtering,
LLM = LLM backend, EV = evaluation.

### 4.1 ContextConflict (EMNLP 2026; arXiv 2609.03148 theo README) — 25 file `.py`, 9.593 LOC, 5.781 file JSON

Cây thư mục: `ContextConflict_Dataset/data/{ambiguity, temporal, granularity, inferential, misinformation, perspective}_conflict/…`,
`evaluation/` (sinh câu trả lời, Shapley attribution, accuracy, balance, faithfulness), `analysis/` (concept vector, spectral energy, position bias).

| Nhóm | Symbol — vị trí | Ghi chú |
|---|---|---|
| DL | `ConflictAwareDataLoader` — `third_party/context_conflict_emnlp_2026/analysis/conflict_aware_data_loader.py:50` | Mỗi loại conflict có một hàm xử lý riêng, ví dụ `process_ambiguity_conflict` — `third_party/context_conflict_emnlp_2026/analysis/conflict_aware_data_loader.py:169` |
| DL | dữ liệu [data] | ambiguity 1.000 (AmbigDocs: cùng tên, khác người; có `ambiguous_entity`); temporal 62 + 898 (62 file ở gốc: số lượng bằng đúng 62 câu "outdated" của CONFLICTS, paper ghi CONFLICTS là một nguồn [tr. 3], và mẫu đầu là câu Passover của CONFLICTS; việc trùng **toàn bộ** là suy luận); granularity 945 (ROAST-ABSA) + 75 (medical_qa); misinformation 632 + 372, có **`accuracy_labels` theo từng source**; inferential 787; perspective 1.010 |
| RET | không có | Evidence được cho sẵn (2–6 source/mẫu). |
| KG | không có | — |
| CF | không có bộ phát hiện conflict | Chỉ có phân tích: probe concept vector, spectral energy, position bias. |
| LLM | `call_llm_api` — `third_party/context_conflict_emnlp_2026/evaluation/generate_responses_api.py:88-96` | `AsyncOpenAI(base_url=OPENAI_BASE_URL)` → trỏ sang vLLM được; có thêm bản sinh local bằng HF. |
| EV | `exact_match` — `third_party/context_conflict_emnlp_2026/evaluation/accuracy.py:275` | Accuracy cho các tác vụ reasoning. |
| EV | `calculate_gini_coefficient` — `third_party/context_conflict_emnlp_2026/evaluation/balance_score.py:86` | Balance = normalized Gini trên Shapley attribution (summarization). |
| EV | `APIGenerativeModel` — `third_party/context_conflict_emnlp_2026/evaluation/evaluator.py:141` | Shapley attribution và chấm claim. |

**Code của steering method chưa được công bố.** Paper đề xuất steering training-free bằng u(l) = (μ̄ − c̄)/‖μ̄ − c̄‖ và
h ← h + α·u với α = 1,0 [paper tr. 8]. Trong repo, các hook chỉ **đọc** activation:
`_current_activations` — `third_party/context_conflict_emnlp_2026/analysis/position_bias/evidence_collector.py:188` (`clone().detach()`).
Tham số liên quan còn được ghi chú rõ là không dùng: `steering_layers` — `third_party/context_conflict_emnlp_2026/analysis/position_bias/directional_bias.py:417-418`
("Kept for interface compatibility with the steering code; not used"). README chỉ liệt kê lệnh cho §3 và §4.1–4.3, không có §5 (steering).

### 4.2 Decision-model conflict typing (Khatri et al., arXiv 2610.36915) — 17 file `.py`, 2.366 LOC

Cây thư mục: `src/dmconflict/` (data, prompts, client, methods, cascade, perturb, metrics, endtoend, run), `runs.nosync/` (**mọi output model**
dùng trong paper, 139 file JSONL), `data/{splits.json, plants.json}`, `human_eval/`, `paper/` (LaTeX), `tests/`.

| Nhóm | Symbol — vị trí | Ghi chú |
|---|---|---|
| DL | `load` — `third_party/decision-models-conflict-typing/src/dmconflict/data.py:29` | Đọc `data/conflicts.jsonl`; split dev/test cố định. |
| DL | `SHA256` — `third_party/decision-models-conflict-typing/scripts/download_data.sh:9` | sha256 của file CONFLICTS **trùng** với `third_party/rag_conflicts/conflicts.jsonl` (đã kiểm bằng `sha256sum`). |
| RET / KG | không có | Dùng search result có sẵn của CONFLICTS. |
| CF | `PAPER_PROMPT` — `third_party/decision-models-conflict-typing/src/dmconflict/prompts.py:15-18` | Prompt nguyên văn của Cattan et al.; mục 1 ghi "Differences are superficial, such as variations in detail or granularity". |
| CF | `flat` — `third_party/decision-models-conflict-typing/src/dmconflict/methods.py:80` | Hỏi trực tiếp 5 lớp; ngoài ra có `tree` (yes/no, dòng 90) và `paper_llm` (dòng 110). |
| CF | `escalate_mask` — `third_party/decision-models-conflict-typing/src/dmconflict/cascade.py:18` | Cascade: phần query có confidence thấp nhất được chuyển lên LLM. |
| CF | `plant` — `third_party/decision-models-conflict-typing/src/dmconflict/perturb.py:90-104` | Thay đáp án đúng bằng đáp án sai trong **một** kết quả (regex nguyên từ) → nhãn Misinformation. Tái dùng được (Apache-2.0). |
| LLM | `GATEWAY` — `third_party/decision-models-conflict-typing/src/dmconflict/client.py:19` | Vercel AI Gateway (`Gateway` dùng `/v1/evaluate`, `Chat` dùng `/v1/chat/completions`) → **API trả phí**; URL viết cứng, muốn dùng vLLM local phải cài lại client. |
| EV | `macro_f1` — `third_party/decision-models-conflict-typing/src/dmconflict/metrics.py:24` | Có `ece`, `paired_bootstrap`, `mcnemar_exact` (dòng 39, 62, 68). |
| EV | `cmd_evaluate` — `third_party/decision-models-conflict-typing/src/dmconflict/run.py:140` | Tính lại bảng kết quả **từ output đã lưu**, không gọi API. |

Kiểm tra tái lập: tôi định chạy `dmconflict evaluate` trên một bản sao trong scratchpad, nhưng auto-mode classifier **chặn** việc cài và
chạy code bên thứ ba ("Code from External"). Tôi không vòng tránh. Kiểm tĩnh được: bảng `runs.nosync/comparison_test.md` có trong repo,
và giá trị cao nhất (`pplx-decider-v1.2 flat` 0,667) khớp với "50.0–67.0%" trong README. Phần **tính lại: chưa làm**.

### 4.3 MemGraphRAG (KDD 2026; arXiv 2606.00610) — 46 file `.py`, 6.121 LOC

Cây thư mục: `code/index.py`, `code/retrieval_dataset_test.py`, `code/src/{MemGraphRAG.py, Memory.py, embedding_store.py}`,
`code/src/{llm, information_extraction, embedding_model, prompts, evaluation, utils}/`, `dataset/`. README ghi "accepted by KDD'26"
(`KDD` — `third_party/MemGraphRAG/README.md:14`).

| Nhóm | Symbol — vị trí | Ghi chú |
|---|---|---|
| DL | `ThreeLayerMemory` — `third_party/MemGraphRAG/code/src/Memory.py:67` | Bộ nhớ 3 lớp: schema (type, relation, type), fact (triple), passage. |
| KG | `OpenIE` — `third_party/MemGraphRAG/code/src/information_extraction/openie_openai.py:36` | NER + triple extraction bằng LLM (kế thừa HippoRAG). |
| KG | `extract_memory_schema` — `third_party/MemGraphRAG/code/src/MemGraphRAG.py:358` | Quy nạp ontology (type-level triple); `filter_memory_ontology` (dòng 452) lọc schema hiếm. |
| KG | `add_synonymy_edges` — `third_party/MemGraphRAG/code/src/MemGraphRAG.py:1418` | "Synonym" dựa trên **độ tương tự embedding** → không có alias có thời gian hiệu lực. |
| CF | `_conflict_candidates` — `third_party/MemGraphRAG/code/src/MemGraphRAG.py:496-527` | Chỉ ghép cặp fact **cùng (subject, relation)** nhưng khác object, cộng kiểm tra quan hệ đảo chiều → không bắt được alias của subject hay predicate liên quan. |
| CF | `detect_memory_conflicts` — `third_party/MemGraphRAG/code/src/MemGraphRAG.py:529` | LLM gán `conflict_type`; bỏ các nhãn duplicate/none/uncertain và các mục dưới ngưỡng confidence. |
| CF | `conflict_min_confidence` — `third_party/MemGraphRAG/code/src/utils/config_utils.py:189` | = **0.85** (chỉ nhận hard conflict có confidence cao). |
| CF | `conflict_detection` — `third_party/MemGraphRAG/code/src/prompts/prompt.py:351-382` | Taxonomy: **mutual / temporal / granularity**; "Be conservative: avoid false positives". |
| CF | `globally_unique` — `third_party/MemGraphRAG/code/src/prompts/prompt.py:368-373` | LLM tự phán **predicate uniqueness** (globally_unique / moment_unique / multi_valued); chỉ 2 loại đầu mới có thể thành hard mutual conflict. |
| CF | `granularity` — `third_party/MemGraphRAG/code/src/prompts/prompt.py:378-379` | "city-country … treat as compatible granularity difference". |
| CF | `conflict_resolution` — `third_party/MemGraphRAG/code/src/prompts/prompt.py:422-445` | mutual → giữ triple đúng; temporal → thêm thời gian vào relation; granularity → thêm scope (ví dụ "born in Shanghai" vs "born in China"). |
| RET | `retrieve` — `third_party/MemGraphRAG/code/src/MemGraphRAG.py:1038` | Embedding + Personalized PageRank (`run_ppr`, dòng 2299); `rerank_facts` (dòng 2186). |
| LLM | `CacheOpenAI` — `third_party/MemGraphRAG/code/src/llm/openai_gpt.py:103-129` | `OpenAI(base_url=llm_base_url)` → vLLM server được; ngoài ra có `VLLMOffline`. |
| EV | `QAExactMatch` — `third_party/MemGraphRAG/code/src/evaluation/qa_eval.py:13` | Có `QAF1Score` và `RetrievalRecall`. |

Lưu ý phần cứng: `vllm` — `third_party/MemGraphRAG/requirements.txt:3-5` (pin `vllm==0.6.6.post1`, `torch==2.5.1`). Các phiên bản này
**rất có thể chưa hỗ trợ RTX 5090 (Blackwell, sm_120)**: **[UNVERIFIED — phải kiểm trên máy thật]**. Cách tránh là chạy LLM qua một vLLM
server riêng, phiên bản mới, rồi trỏ `--llm-base-url` vào đó. TruthfulRAG cũng pin `torch==2.5.1`.

## 5. Kiểm chứng các mục [UNVERIFIED] của Phase A (giờ đã có full text)

| Claim ở Phase A (chỉ dựa trên snippet tìm kiếm) | Kết quả kiểm chứng | Nguồn |
|---|---|---|
| HVM-GraphRAG phân loại mutual/temporal/granularity bằng prompt | **Đúng.** Chạy lúc dựng graph (holistic view), dữ liệu là QA tài liệu đa phương thức (MMLongBench, M3DocVQA, Qasper), dùng Qwen3-8B-AWQ. **Không có link code** trong PDF. Chung tác giả Qinggang Zhang với MemGraphRAG/GraphRAG-Bench. | [paper HVM tr. 1, 3–4, 6–7, 21, 25–26] |
| MemGraphRAG có taxonomy tương tự | **Đúng, và có code (MIT).** Prompt + ngưỡng nêu ở §4.3; Table 8 định nghĩa mutual là xung đột trên "functional property (single-value attribute)". **Không** đo riêng độ chính xác của detector (chỉ ablation QA, "w/o Conflict Resolution"). | `conflict_detection` — `third_party/MemGraphRAG/code/src/prompts/prompt.py:351-382`; [paper MemGraphRAG tr. 8, 14] |
| EvoTrustRAG có "wrong-filtering rate" | **Đúng.** "WFR is the fraction of queries for which the method removes at least one evidence item that should remain available under the gold attribution" → **mức query**, gắn với attribution evolution/intervention/unresolved; không có alias/granularity/homonym. Baseline gồm cả TruthfulRAG. **Không có link code** trong PDF. | [paper EvoTrustRAG tr. 1, 4–5] |
| ConflictRAG: filter self-reflection loại cả evidence | **Đúng, nhưng chỉ là giả thuyết của tác giả**: "Self-RAG scores below Standard RAG (47.8% vs. 49.2% on ConflictQA), likely because its reflection filter over-removes contradictory evidence". Taxonomy: no-conflict / factual / temporal / opinion; detector 2 tầng (MLP + LLM). **Không có link code.** | [paper ConflictRAG tr. 1–4] |
| CONFLICTS (Cattan et al.) | Tác giả thuộc **Google Research + Bar-Ilan University**; taxonomy coi khác biệt **granularity là "No conflict"**; annotate **mức query** bởi chuyên gia (3 bước); typing tốt nhất là Gemini 2.5 Flash 65,3%. | [paper CONFLICTS tr. 1–2, 4–5, 8] |

**Điều này thay đổi đánh giá novelty ở `03`:** khung "granularity tương thích, temporal phụ thuộc thời gian, mutual là genuine" **đã có** dưới dạng
prompt LLM ở bước dựng graph (MemGraphRAG KDD'26; HVM-GraphRAG). Novelty của G2 phải chuyển sang những gì họ chưa làm (xem `03` mục G2).

## 6. (e) Mở rộng 3 thuật toán này thành bài journal Open Access (IEEE Access / PLOS ONE / Scientific Reports)?

### 6.1 Tiêu chí venue (đã kiểm qua WebSearch ở Phase A; trang gốc chưa mở trong sandbox)

- **IEEE Access**: binary review; "original, technically correct, clearly presented"; bài không có tiến bộ rõ so với SOTA có thể bị desk reject; APC 2.075 USD (**[UNVERIFIED]**).
- **PLOS ONE**: chấm **technical rigor**, không chấm "perceived novelty/impact"; bắt buộc công bố dữ liệu; APC **[UNVERIFIED]**.
- **Scientific Reports**: "scientifically valid and technically sound" (theo Wikipedia dẫn Guide to Referees; trang gốc **[UNVERIFIED]**).

Hệ quả: **IEEE Access** cần một **phương pháp** tốt hơn rõ rệt. **PLOS ONE / Scientific Reports** chấp nhận được một **nghiên cứu thực nghiệm chặt chẽ**
(kể cả kết quả âm), miễn thiết kế tốt, có thống kê và dữ liệu/code mở. Không venue nào bảo đảm accept.

### 6.2 MemGraphRAG → **Có, có điều kiện**. Liên quan nhất tới Paper 3.

- **Khe hở kiểm chứng được**: (i) detector conflict **chưa từng được đo** độ chính xác hay false-positive rate (paper chỉ có ablation QA [tr. 8]);
  (ii) uniqueness và containment do **LLM tự phán** (`globally_unique` — `third_party/MemGraphRAG/code/src/prompts/prompt.py:368-373`) thay vì tra
  KG schema; (iii) candidate chỉ là cặp cùng (subject, relation), nên alias của subject, homonym và predicate liên quan bị bỏ sót
  (`_conflict_candidates` — `third_party/MemGraphRAG/code/src/MemGraphRAG.py:496-527`); (iv) chỉ chạy lúc dựng index, không áp được cho
  **fixed candidate pool** lúc truy vấn.
- **Hướng mở rộng**: thay hoặc bổ sung phán đoán LLM bằng **KG schema** (ràng buộc single-value của property, bao đóng P131/P361,
  qualifier P580/P582, alias có thời gian hiệu lực, type P31) theo kiểu **"KG-first, LLM-fallback"**; đo typing F1 theo loại, false hard-conflict
  rate và **số lần gọi LLM tiết kiệm được**; cắm vào pipeline MemGraphRAG (MIT cho phép) **và** dùng cho reranking lúc truy vấn (G2).
  Prompt của MemGraphRAG trở thành **baseline LLM-typer** sẵn có.
- **Khả thi trên 1× RTX 5090**: được, nếu chạy LLM 7–8B qua vLLM server mới. Chi phí indexing (OpenIE + schema + detect + resolve) phải ước tính ở Phase C
  (`06`). Cần lưu ý pin torch/vLLM cũ.
- **Venue**: IEEE Access nếu cho thấy typing tốt hơn rõ rệt hoặc rẻ hơn mà QA không giảm; PLOS ONE / Sci Rep nếu trình bày như
  **benchmark + đánh giá detector conflict trong GraphRAG** (phần đang thiếu).
- **Rủi ro**: nhóm XMU DeepLIT/JLU ra bài rất nhanh (GraphRAG-Bench ICLR'26, MemGraphRAG KDD'26, HVM-GraphRAG 7/2026 dùng lại taxonomy),
  nên **rủi ro bị đi trước là cao**; cần Wikidata (bị chặn trên cloud, phải dùng dump trên máy local).

### 6.3 ContextConflict → **Có, có điều kiện**, nhưng **ít khớp** với hướng KG của Paper 3.

- **Khe hở do chính tác giả nêu** [tr. 9]: steering mới chạy ở 8B/20B; dữ liệu synthetic ("evaluating on noisy, real-world retrieval with heterogeneous evidence
  remains open"); Shapley giả định mọi evidence đóng góp như nhau ("weighted Shapley … with source-reliability priors" là hướng mở).
- **Hướng mở rộng**: (a) áp steering lên **pool retrieval thật** (CONFLICTS, 2Wiki) và so với cách rẻ hơn là **reorder/rerank** evidence để giảm
  position bias; (b) steering có tính tới loại conflict hoặc độ tin cậy của nguồn (dùng tín hiệu typing của G2); (c) dùng subset `ambiguity`
  (≈ homonym), `temporal`, `misinformation` (có nhãn theo source) làm dữ liệu đánh giá cho typing.
- **Khả thi**: steering cần can thiệp hidden state (HF `transformers` + hook); API OpenAI-compatible chuẩn của vLLM không cho làm việc này (plugin
  hay chế độ khác của vLLM: **[UNVERIFIED]**); model 7–8B vừa với 32 GB. Code steering
  **chưa công bố** → phải tự cài lại từ Eq. 6 [tr. 8]; rủi ro sai khác với bản gốc.
- **Venue**: Sci Rep / PLOS ONE hợp với dạng **replication + generalization** (steering trên pool thật, nhiều họ model, thống kê chặt);
  IEEE Access cần biến thể steering mới có lợi rõ.
- **Rủi ro**: **không có license** (cả repo lẫn dataset card), phải hỏi tác giả trước khi dùng dữ liệu trong bài; mechanistic interpretability lệch
  khỏi chủ đề KG-guided reranking (ảnh hưởng tính mạch lạc của luận án).

### 6.4 Decision-model conflict typing → **Có, có điều kiện**. Rẻ nhất và tái lập tốt nhất.

- **Khe hở do chính tác giả nêu** [tr. 10]: CONFLICTS nhỏ (406 test; chênh lệch dưới khoảng 5 điểm không có ý nghĩa thống kê); chỉ 5 misinformation tự nhiên;
  biến thể planted chỉ thử **một kiểu** misinformation (thay entity/value); model hosted thay đổi theo thời gian; judge cùng model với generator; không đo
  factual grounding. Thêm vào đó, typing chỉ ở **mức query**, và mọi decision model đều là **dịch vụ trả phí** (gateway URL viết cứng).
- **Hướng mở rộng**: (a) **typer open-weight chạy local** (LLM 7–8B lấy xác suất trên các lựa chọn, hoặc NLI/cross-encoder) thay cho decision model
  hosted → tái lập được; (b) **typing mức source/cặp** + **cascade KG-first** (rule KG trước, LLM khi KG không phủ); (c) **planted apparent conflict**
  (alias, granularity, temporal) để đo false alarm "Misinformation", tức over-filtering (G7), tái dùng khung `plant` và diagnostics (Apache-2.0).
- **Khả thi**: cao, chủ yếu CPU + LLM 7–8B; output gốc có sẵn để so sánh. **Không** chạy lại decision model hosted (cần API trả phí; trái quy tắc 4
  nếu không có ngân sách).
- **Venue**: PLOS ONE / Sci Rep rất hợp (bài gốc đã theo phong cách pre-registered); IEEE Access cần (b) cho kết quả rõ.
- **Rủi ro**: bài gốc mới ra (10/2026) và lĩnh vực đang đông; nếu chỉ "thay model" thì dễ bị coi là incremental.

### 6.5 Kết luận tổng hợp và khuyến nghị

| Phương án | Venue phù hợp nhất | Novelty risk | Khả thi trên 1× RTX 5090 | Khớp chủ đề Paper 3 |
|---|---|---|---|---|
| A. **Một bài hợp nhất**: KG-schema typing (KG-first, LLM-fallback) cho apparent vs genuine + reranking trên fixed pool; baseline = prompt MemGraphRAG, verifier kiểu ArbGraph, entropy filter TruthfulRAG; metric FCFR/GER (passage) + WFR (query, kiểu EvoTrustRAG) | IEEE Access (nếu kết quả mạnh) / PLOS ONE | trung bình | cao | **rất cao** |
| B. Nghiên cứu thực nghiệm "false conflicts": đo over-filtering của các detector/filter (MemGraphRAG/HVM prompt, ArbGraph, TruthfulRAG, NLI, typer kiểu decision model) theo từng loại apparent | PLOS ONE / Sci Rep | trung bình (EvoTrustRAG có WFR mức query) | cao | cao |
| C. Mở rộng MemGraphRAG riêng (KG-schema thay phán đoán LLM ở bước dựng index) | IEEE Access | trung bình–cao (rủi ro bị đi trước) | trung bình (chi phí indexing) | cao |
| D. Mở rộng decision-model typing riêng (open-weight + mức source) | PLOS ONE / Sci Rep | trung bình–cao | cao | trung bình |
| E. Mở rộng steering của ContextConflict | Sci Rep / PLOS ONE | trung bình | trung bình (code chưa có) | thấp |

**Trả lời ngắn:** Có thể. Cả ba hướng đều có khe hở thật, được chính tác giả thừa nhận hoặc kiểm chứng được trong code, và đều chạy được trên
phần cứng của bạn. Nhưng **không có gì bảo đảm accept**. Cách tôi khuyến nghị là **không mở rộng riêng lẻ từng bài**, mà viết **bài A**, dùng ba
công trình này làm baseline, nguồn dữ liệu và động lực: MemGraphRAG cung cấp taxonomy dạng prompt để so sánh; decision-model typing cung cấp ý
tưởng cascade, khung planted và dữ liệu CONFLICTS đã cố định; ContextConflict cung cấp subset ambiguity/temporal/misinformation (sau khi xin phép).
Phương án B là "lưới an toàn" hợp với PLOS ONE / Sci Rep nếu phần phương pháp của A không vượt baseline rõ.

## 7. Mục [UNVERIFIED] và việc cần làm phát sinh

1. License của dữ liệu ContextConflict (repo và HF card không khai báo) → cần email tác giả trước khi dùng trong bài.
2. RTX 5090 có chạy được `torch==2.5.1` / `vllm==0.6.6.post1` (MemGraphRAG, TruthfulRAG) không → kiểm trên máy thật.
3. License phần code kế thừa HippoRAG trong MemGraphRAG.
4. Tính lại số liệu của decision-model typing từ output đã lưu (bị chặn chạy code bên thứ ba ở cloud; có thể làm trên máy local, hoặc bạn cấp quyền).
5. Code của HVM-GraphRAG, EvoTrustRAG, ConflictRAG: **không có link trong PDF** → nếu cần audit, phải hỏi tác giả.
6. Nguyên nhân WebFetch vẫn không phân giải được `arxiv.org`.
