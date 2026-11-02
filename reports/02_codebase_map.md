# 02 — Codebase map và trả lời (a)–(d) (Phase A, chỉ đọc)

> Audit chỉ đọc. Số dòng ứng với đúng các commit ở §1. Ký hiệu nguồn: **[code]** = đọc trực tiếp code;
> **[paper tr. X]** = PDF bạn attach (số trang của file PDF); **[README]**; **[search]** = chỉ thấy qua
> WebSearch (chưa đọc full text) → luôn kèm **[UNVERIFIED]**.
> Tái lập:
> `python3.11 -I scripts/audit/inventory.py third_party/* --out logs/audit` (cây thư mục, LOC, index `def`/`class`) và
> `python3.11 -I scripts/audit/check_citations.py reports/0[1-3]_*.md` (kiểm mọi trích dẫn `path:line`).

## 1. Clone upstream và commit

Lệnh: `git clone --depth 1 <upstream> third_party/<Repo>` (log đầy đủ: `logs/audit/clone_attempts.log`, gitignored).

| Repo | Upstream | Exit | Upstream HEAD | Fork `Thuy-g/*` HEAD | Trùng? | Commit date |
|---|---|---|---|---|---|---|
| TruthfulRAG | github.com/STAIR-BUPT/TruthfulRAG | 0 | `231c9175f51a71a2407e38b8213f8ac910d46a6d` | như upstream | ✅ | 2025-12-18 |
| GraphRAG-Benchmark | github.com/GraphRAG-Bench/GraphRAG-Benchmark | 0 | `fdbab5959b18c96532580877ffe27d112bccc0ec` | như upstream | ✅ | 2026-06-07 |
| MAGIC | github.com/HYU-NLP/MAGIC | 0 | `f3df32cb85ff84dbfc17cd8870f82f13aa9647d3` | như upstream | ✅ | 2026-09-04 |
| rag_conflicts (CONFLICTS) | github.com/google-research-datasets/rag_conflicts | 0 | `81ba921dd684a93db41a7e9dda6b6a7c67348a88` | như upstream | ✅ | 2025-06-11 |
| ArbGraph | github.com/1212Judy/ArbGraph | 0 | `d98950fbf6b5ea45008d98e9dc582054ffe81c05` | như upstream | ✅ | 2026-09-03 |
| Relink | github.com/DMiC-Lab-HFUT/Relink | 0 | `135526bb0694d7eb4120c8d4d48bfe3ffd694124` | như upstream | ✅ | 2026-03-20 |
| kapipe (ProStruct-RAG) | github.com/norikinishida/kapipe | 0 | `89aaeb94653698a13159bfc3168091c8527eb895` | như upstream | ✅ | 2026-10-27 |

Ghi chú:
- Lần chạy đầu bị **bạn ngắt** khi đang clone GraphRAG-Benchmark (TruthfulRAG đã xong, exit 0); lần chạy lại
  thành công cả 6 repo còn lại. Không có lỗi 403 nào khi `git clone`.
- **Đính chính Phase 0**: probe HTTP tới trang web `github.com/STAIR-BUPT/TruthfulRAG` trả 403, nhưng
  `git clone` qua git proxy với repo public thì **chạy được**. `reports/00_environment.md` đã được sửa.
- HEAD của 7 fork trùng HEAD upstream (kiểm bằng `git rev-parse HEAD` hai phía) → mục [UNVERIFIED]
  "fork == upstream" của Phase 0 đã được giải quyết.
- Dung lượng clone: ~207 MB, phần lớn là **dữ liệu đi kèm repo** (Relink `data/` 65 MB, `conflicts.jsonl` 45 MB).
  Đây là nguồn audit, không phải data slice thí nghiệm; `third_party/` không được commit.

## 2. LICENSE và hệ quả khi reuse

| Repo | LICENSE | Hệ quả thực tế cho dự án |
|---|---|---|
| TruthfulRAG | Apache-2.0 | Được dùng, sửa, tái phân phối; phải giữ license + ghi rõ thay đổi; có patent grant. Có thể port `entropy_filter` thành baseline (ghi attribution). |
| GraphRAG-Benchmark | MIT, "Copyright (c) 2025 XMU-DeepLIT" | Rất thoáng: giữ copyright notice là đủ. License của corpus (tiểu thuyết Gutenberg + NCCN guideline) chưa kiểm: **[UNVERIFIED]**. |
| MAGIC | CC-BY-4.0 (dataset) | Dùng/biến đổi dữ liệu được, bắt buộc attribution. Dữ liệu sinh từ Wikidata5M + GPT-4o-mini [paper tr. 3, 5]. |
| rag_conflicts | Apache-2.0 (file LICENSE) | File license là Apache-2.0, nhưng nội dung là **trang web bên thứ ba** (`response_str` = full text) → không tái phân phối text thô; chỉ dùng local. README: "This is not an official Google's product". |
| ArbGraph | **Không có file LICENSE** | Mặc định **all rights reserved**: được đọc/trích dẫn, **không** được copy code vào repo của mình hay phát hành lại. README chỉ ghi "released for research use and partial reproducibility" — không phải license grant. Muốn reuse: tự **cài đặt lại từ mô tả trong paper** hoặc xin phép tác giả. README nhắc repo chính thức `RUCAIBox/ArbGraph`, license ở đó **[UNVERIFIED]**. |
| Relink | MIT, "Copyright (c) 2025 DMiC-Lab-HFUT" | Thoáng. Các dataset đi kèm (HotpotQA, 2WikiMultiHopQA, MuSiQue, ConcurrentQA) có license riêng: **[UNVERIFIED]**, phải kiểm trước khi dùng slice. |
| kapipe | Apache-2.0 (`pyproject.toml`: `license = { text = "LICENSE" }`) | Như TruthfulRAG; dùng như thư viện (`pip install kapipe`) là sạch nhất. |

Trích dẫn license/README:
- `reproducibility` — `third_party/ArbGraph/readme.md:16`
- `RUCAIBox` — `third_party/ArbGraph/readme.md:12`
- `GPU` — `third_party/ArbGraph/readme.md:73`
- `Disclaimer` — `third_party/rag_conflicts/README.md:42`

## 3. Bản đồ từng repo

Quy ước cột "Nhóm": DL = data loading, RET = retrieval, KG = KG construction & triple extraction,
CF = conflict detection & filtering, LLM = LLM backend, EV = evaluation.

### 3.1 TruthfulRAG (AAAI 2026) — 20 file `.py`, 3.686 LOC

Cây thư mục: `truthfulrag/` gồm `__init__.py, base.py, evaluate.py, modules.py, pipeline.py, prompts.py, utils.py`,
`kg/{__init__.py, nano_vector_db_impl.py, networkx_impl.py}`, `llm/{__init__.py, backend.py, hf.py, ollama.py, openai.py}`,
`util/{__init__.py, format_util.py, logger.py}`; `datas/` gồm 6 file JSON (chi tiết ở câu (b)); demo: `openai_demo.py`, `hf_demo.py`, `test.ipynb`.

| Nhóm | Symbol — vị trí | Ghi chú |
|---|---|---|
| DL | `chunking_by_token_size` — `third_party/TruthfulRAG/truthfulrag/modules.py:36` | Mỗi ví dụ có **một** chuỗi `context`; chunk 1024 token, overlap 128 (tiktoken). Không có pool passage. |
| DL | `split_by_sentence` — `third_party/TruthfulRAG/truthfulrag/utils.py:551` | Dùng ở ablation "w/o KG" để tách context thành câu. |
| KG | `generate_knowledge_graph` — `third_party/TruthfulRAG/truthfulrag/modules.py:57` | Trích entity/relationship bằng LLM kiểu LightRAG (có 1 vòng "gleaning"). |
| KG | `_handle_single_entity_extraction` — `third_party/TruthfulRAG/truthfulrag/modules.py:664` | Tên entity = `clean_str(...upper())` → gộp node theo **chuỗi in hoa**, không có alias/entity linking. |
| KG | `DEFAULT_ENTITY_TYPES` — `third_party/TruthfulRAG/truthfulrag/prompts.py:18` | Chỉ 4 type: organization, person, location, event. |
| RET | `retrieve_knowledge_graph` — `third_party/TruthfulRAG/truthfulrag/modules.py:260` | LLM trích keyword + answer-type từ câu hỏi (`truthfulrag_query2kwd`). |
| RET | `_build_query_context` — `third_party/TruthfulRAG/truthfulrag/modules.py:820` | Vector search tên entity → lân cận 2-hop → chấm path → mỗi element là chuỗi "Path/Nodes/Edges". |
| RET | `get_neighbors_within_k_hops` — `third_party/TruthfulRAG/truthfulrag/kg/networkx_impl.py:128` | Duyệt đồ thị NetworkX. |
| CF | `entropy_filter` — `third_party/TruthfulRAG/truthfulrag/modules.py:351-460` | Bộ lọc dựa trên entropy — phân tích ở câu (b). |
| CF | `entropy_based_filter` — `third_party/TruthfulRAG/truthfulrag/pipeline.py:282` | Wrapper; mặc định `threshold=1`, `top_k=10`. |
| LLM | `LLMBackend` — `third_party/TruthfulRAG/truthfulrag/llm/backend.py:15` | Backend: `openai`, `hf`, `ollama`. |
| LLM | `initialize_openai_client` — `third_party/TruthfulRAG/truthfulrag/llm/openai.py:9-13` | Đọc `OPENAI_BASE_URL` → trỏ sang vLLM local được. |
| LLM | `cal_entroy` — `third_party/TruthfulRAG/truthfulrag/llm/backend.py:147` | Cần `logprobs` + `top_logprobs=10`. |
| EV | `exact_match_score` — `third_party/TruthfulRAG/truthfulrag/evaluate.py:8` | Cùng file có `acc_score` (dòng 11) và `f1_score` (dòng 14); chuẩn hóa ở `normalize_answer` (dòng 39). |
| EV | `evaluate` — `third_party/TruthfulRAG/truthfulrag/pipeline.py:537` | EM/ACC/F1 trên đáp án trích từ output CoT. |

### 3.2 GraphRAG-Benchmark (ICLR 2026) — 18 file `.py`, 3.137 LOC

Cây thư mục: `Datasets/{Corpus, Questions}` (JSON + parquet), `Evaluation/{generation_eval.py, retrieval_eval.py, indexing_eval.py, llm/, metrics/}`,
`Examples/{run_lightrag.py, run_hipporag2.py, run_fast-graphrag.py, run_digimon.py}`. Repo có commit cả file `.pyc`
trong `__pycache__/` (gồm `context_recall.*.pyc` nhưng **không** có `context_recall.py`), dấu hiệu code đã thay đổi theo thời gian.

| Nhóm | Symbol — vị trí | Ghi chú |
|---|---|---|
| DL | `main` — `third_party/GraphRAG-Benchmark/Evaluation/retrieval_eval.py:126` | Đọc JSON list; nhóm theo `question_type`. |
| DL | dữ liệu: `Datasets/Questions/novel_questions.json` (2.010 câu), `medical_questions.json` (2.062 câu); corpus `novel.json` = 20 tiểu thuyết | Trường câu hỏi: `id, source, question, answer, question_type, evidence` (**string**), `evidence_triple`/`evidence_relations`. |
| RET | không có retriever riêng; `Examples/run_*.py` gọi framework ngoài | Ví dụ: `context` — `third_party/GraphRAG-Benchmark/Examples/run_lightrag.py:226` |
| KG | không dựng KG; `analyze_graph` — `third_party/GraphRAG-Benchmark/Evaluation/indexing_eval.py:11` | Chỉ **đánh giá** graph do framework khác dựng (node/edge count, degree, clustering). |
| CF | không có | Không phải benchmark về conflict. |
| LLM | `ChatOpenAI` — `third_party/GraphRAG-Benchmark/Evaluation/retrieval_eval.py:139-152` | Judge qua `--base_url`; mode `ollama` dùng `OllamaClient` (API native của Ollama). |
| EV | `compute_context_relevance` — `third_party/GraphRAG-Benchmark/Evaluation/metrics/context_relevance.py:38` | LLM judge 0–2 (chi tiết ở câu (a)). |
| EV | `compute_evidence_recall` — `third_party/GraphRAG-Benchmark/Evaluation/metrics/evidence_recall.py:49` | LLM judge theo từng evidence statement. |
| EV | `compute_answer_correctness` — `third_party/GraphRAG-Benchmark/Evaluation/metrics/answer_accuracy.py:147` | 0.75 × factuality (LLM) + 0.25 × cosine của embedding. |
| EV | `compute_rouge_score` — `third_party/GraphRAG-Benchmark/Evaluation/metrics/rouge.py:4` | Không cần LLM. |

### 3.3 MAGIC (Findings EMNLP 2025) — chỉ có dữ liệu, 0 file `.py`

Cây thư mục: `dataset/single-hop/{1..4}-single-hop_conflict.json`, `dataset/multi-hop/{1..4}-multi-hop_conflict.json`, `LICENSE` (CC-BY-4.0), `README.md`.
Repo **không có code** sinh dữ liệu hay đánh giá (khớp với tên file PDF "NO-CODE" bạn đặt).

| Nhóm | Vị trí | Ghi chú |
|---|---|---|
| DL | `rel_id` … `context2` — `third_party/MAGIC/README.md:46-50` | `id, rel_id, subgraph, original_triplet, perturb_triplet, context1, context2` (format chi tiết ở câu (c)). |
| KG | (offline, không có trong repo) | Wikidata5M, 46/825 relation, DFS subgraph [paper tr. 3]. |
| CF | — | Tác vụ: phát hiện (ID) + định vị (LOC) conflict giữa `context1` và `context2`; **chấm thủ công** [paper tr. 6]. |
| RET / LLM / EV | không có | — |

### 3.4 CONFLICTS (`rag_conflicts`) — chỉ có dữ liệu

`conflicts.jsonl` (458 dòng, 46,7 MB) và `README.md`. Trường dữ liệu: `response_str` — `third_party/rag_conflicts/README.md:20`;
`short_text` (cửa sổ 512 token) — `third_party/rag_conflicts/README.md:21`; nhãn `conflict_type` — `third_party/rag_conflicts/README.md:24`.
Không có code. Paper gốc (Cattan et al. 2025, arXiv 2506.08500) **không được attach** → chi tiết paper gốc ghi [UNVERIFIED].
Phân tích format ở câu (c).

### 3.5 ArbGraph (arXiv 2604.18362) — 9 file `.py`, 937 LOC

Cây thư mục: `atomization.py, claim_alignment.py, evidence_graph.py, conflict_arbitration.py, longform_generation.py, structures.py, run_arbgraph.py`,
`retrieval/retriever.py`, `local_llm/hf_adapter.py`, `readme.md`, `requirements.txt`. **Không có** thư mục `data/` hay LICENSE.

| Nhóm | Symbol — vị trí | Ghi chú |
|---|---|---|
| DL | `main` — `third_party/ArbGraph/run_arbgraph.py:142-170` | Đọc `data/longfact/longfact_test.json` — file **không có trong repo**. |
| RET | `WikipediaRetriever` — `third_party/ArbGraph/retrieval/retriever.py:27` | Gọi **API Wikipedia trực tiếp** (`api.php` ở dòng 64 và 96) → kết quả thay đổi theo thời gian; `max_docs=5` (`run_arbgraph.py:73`). |
| KG | `ClaimExtractor` — `third_party/ArbGraph/atomization.py:7` | LLM tách atomic claim (không phải triple). |
| KG | `NodeAligner` — `third_party/ArbGraph/claim_alignment.py:7-92` | Gộp claim nếu cosine ≥ `similarity_threshold`=0.88 **và** có key term chung, cùng năm, cùng số → không có alias. |
| KG | `EvidenceGraphBuilder` — `third_party/ArbGraph/evidence_graph.py:8-99` | Lọc theo query (τ_q=0.3), chọn cặp theo cosine, LLM gán nhãn quan hệ. |
| CF | `_verify_relation` — `third_party/ArbGraph/evidence_graph.py:157-190` | Nhãn **chỉ** gồm support / contradiction / neutral + confidence. |
| CF | `ArbGraphArbitrator` — `third_party/ArbGraph/conflict_arbitration.py:17-233` | Trọng tài lặp; credibility = sigmoid(logit) (chi tiết ở câu (d)). |
| LLM | `HFAdapter` — `third_party/ArbGraph/local_llm/hf_adapter.py:7-35` | HF `transformers` local; prompt đưa thẳng vào tokenizer, **không áp chat template**. |
| EV | không có trong repo | Paper dùng LongFact + RAGChecker [paper tr. 11]. |

Sai khác code ↔ README/paper (cần ghi nhớ khi tái lập):
- `pair_similarity_threshold` — `third_party/ArbGraph/evidence_graph.py:24` mặc định 0.75, trong khi README ghi τ_sim = 0.65.
- `max_rounds` — `third_party/ArbGraph/run_arbgraph.py:157` = 2, trong khi README ghi T = 3.

### 3.6 Relink (AAAI 2026) — 28 file `.py`, 7.153 LOC

Cây thư mục: `core/{KG_extraction.py, retriever.py, path_ranker.py, llm_functions.py, generator.py, feedback.py, prompt_list.py}`,
`app/{path_scorer.py, path_score_server.py}`, `training_process/` (train path scorer / relation encoder),
`data/{hotpot, wikiMQA, MuSiQue, MuSiQue_Ans, ConcurrentQA}`, `my_evaluate/`, `run_config/*.yaml`, `utils/`.
Hạ tầng cần có: Redis + Neo4j qua docker (README dòng 24–25) và trọng số path scorer tải từ Google Drive (README dòng 37).

| Nhóm | Symbol — vị trí | Ghi chú |
|---|---|---|
| DL | `load_and_chunk_documents` — `third_party/Relink/core/KG_extraction.py:94` | `data/wikiMQA/dataset/samples.json` = **500 mẫu 2WikiMultiHopQA** (có `context`, `supporting_facts`, `evidences` triple, `answer`). |
| KG | `run_kg_extraction_pipeline` — `third_party/Relink/core/KG_extraction.py:264` | LLM trích triple; KG lưu trong Neo4j. |
| RET | `GraphRetriever` — `third_party/Relink/core/retriever.py:25` | Beam search trên KG + co-occurrence graph ("latent relation pool"). |
| CF | `PathRanker` — `third_party/Relink/core/path_ranker.py:28` | Chấm path bằng ranker đã train / embedding / LLM → loại "distractor facts". |
| CF | `PathScorer` — `third_party/Relink/app/path_scorer.py:322` | Mạng neural (TripleEncoder, CrossAttention); **cần train**. |
| LLM | `OpenAI` — `third_party/Relink/utils/my_llm.py:163` | `base_url` cấu hình được → vLLM được. Embedding mặc định `text-embedding-3-small` (`configs.py:89`, API **trả phí**). |
| EV | `eval_on_hotpot_dataset` — `third_party/Relink/my_evaluate/hotpot_evaluate_v1.py:119` | EM/F1 kiểu HotpotQA. |

### 3.7 kapipe / ProStruct-RAG (EMNLP 2026) — 196 file `.py`, 41.069 LOC

Thư viện nhiều component: `kapipe/{chunking, ner, ed_retrieval, ed_reranking, docre, proposition_extraction, proposition_relation_extraction, proposition_relation_refinement, passage_retrieval, graph_retrieval, context_formatting, qa, llms, evaluation, pipelines}`;
`experiments/` chứa script cho từng component cùng script tiền xử lý **nhiều dataset** (2wikimultihopqa, hotpotqa, musique, clark_news, streamingqa, …).

| Nhóm | Symbol — vị trí | Ghi chú |
|---|---|---|
| DL | `read_jsonl` — `third_party/kapipe/kapipe/utils.py:55` | Pipeline đọc passages (JSONL) + questions (JSON). |
| RET | `BM25` — `third_party/kapipe/kapipe/passage_retrieval/bm25.py:15` | Ngoài ra có `Contriever`, `Qwen3Embedding`. |
| RET | `reorder_nodes_and_edges_using_timestamp` — `third_party/kapipe/kapipe/graph_retrieval/graph_retriever.py:198` | Sắp xếp subgraph theo timestamp. |
| KG | `LLMPropositionExtractor` — `third_party/kapipe/kapipe/proposition_extraction/llm_proposition_extractor.py:16` | Proposition + timestamp = ngày xuất bản của tài liệu. |
| KG | `ATLOP` — `third_party/kapipe/kapipe/docre/atlop.py:38` | Có docRE (triple extraction) và entity disambiguation: `BlinkBiEncoder`, `BlinkCrossEncoder`, `LLMED`. |
| CF | `LLMPropositionRelationExtractor` — `third_party/kapipe/kapipe/proposition_relation_extraction/llm_proposition_relation_extractor.py:17` | LLM gán `updates / contradicts / supports / NOREL` cho từng cặp proposition. |
| CF | `NOREL` — `third_party/kapipe/kapipe/proposition_relation_extraction/llm_proposition_relation_extractor.py:208-209` | Bỏ các cặp NOREL. |
| CF | `LLMPropositionRelationRefiner` — `third_party/kapipe/kapipe/proposition_relation_refinement/llm_proposition_relation_refiner.py:17` | Bước tinh chỉnh nhãn. |
| LLM | `OpenAILLM` — `third_party/kapipe/kapipe/llms/openai_llm.py:20-34` | `OpenAI()` đọc env (`OPENAI_BASE_URL`) → vLLM được cho `generate`; riêng `submit_batch` dùng OpenAI **Batch API** (vLLM có hỗ trợ hay không: **[UNVERIFIED]**). |
| EV | `ndcg_at_k` — `third_party/kapipe/kapipe/evaluation/passage_retrieval/ndcg_at_k.py:6` | Có sẵn MRR, P/R@k, QA accuracy, token F1 → có thể dùng đối chiếu metric. |

Prompt phân loại quan hệ (định nghĩa dựa trên timestamp, không có hướng dẫn alias/granularity):
`updates` / `contradicts` — `third_party/kapipe/kapipe/proposition_relation_extraction/prompt_templates/prostruct_rag_proposition_relation_extraction_01.txt:13-14`.

---

## 4. Trả lời các câu hỏi bắt buộc

### (a) GraphRAG-Bench: format input, LLM judge, `--base_url`, và chấm một standalone reranker

**Input của `retrieval_eval.py`.** File là một JSON **list**; mỗi item phải có `id`, `question`, `evidence`, `context`,
và tùy chọn `question_type` (thiếu thì gom vào "Uncategorized"):
- `question_type` — `third_party/GraphRAG-Benchmark/Evaluation/retrieval_eval.py:186`
- `evidence` — `third_party/GraphRAG-Benchmark/Evaluation/retrieval_eval.py:202-205` (đọc `id, question, evidence, context`)
- **Không** đọc `generated_answer` ⇒ retrieval eval **không cần** câu trả lời sinh ra.

**`context` là string hay list?** Cả hai đều được với retrieval metrics:
- context relevance: `isinstance` — `third_party/GraphRAG-Benchmark/Evaluation/metrics/context_relevance.py:53-58` (list → nối bằng `\n`; string giữ nguyên)
- evidence recall: `isinstance` — `third_party/GraphRAG-Benchmark/Evaluation/metrics/evidence_recall.py:62-67`
- Cả hai cắt ở **20.000 ký tự**: `context_str` — `third_party/GraphRAG-Benchmark/Evaluation/metrics/context_relevance.py:66`; `context_str` — `third_party/GraphRAG-Benchmark/Evaluation/metrics/evidence_recall.py:75`.
- Riêng **generation eval** thì `context` phải là **list**: `compute_faithfulness_score` gọi `"\n".join(contexts)` mà không kiểm kiểu (`contexts` — `third_party/GraphRAG-Benchmark/Evaluation/metrics/faithfulness.py:89`); truyền string sẽ bị chèn `\n` giữa từng ký tự.
- `evidence` trong dataset là **một string** (không phải list) → được format thẳng vào prompt.

**Input của `generation_eval.py`.** Cần `id, question, ground_truth, generated_answer, context, question_type`
(`generated_answer` — `third_party/GraphRAG-Benchmark/Evaluation/generation_eval.py:231`); item có `question_type` nằm ngoài 4 loại
(`metric_config` — `third_party/GraphRAG-Benchmark/Evaluation/generation_eval.py:198-203`) sẽ bị **bỏ qua**.

**Metric nào cần LLM judge?**

| Metric | LLM judge? | Embedding? | Vị trí |
|---|---|---|---|
| Context Relevance | Có (2 lần, thang 0–2, chia 2) | Không | `rating1` — `third_party/GraphRAG-Benchmark/Evaluation/metrics/context_relevance.py:70-79` |
| Evidence Recall | Có (phân loại "attributed" cho từng evidence) | Không | `classifications` — `third_party/GraphRAG-Benchmark/Evaluation/metrics/evidence_recall.py:79-88` |
| ROUGE-L | Không | Không | `compute_rouge_score` — `third_party/GraphRAG-Benchmark/Evaluation/metrics/rouge.py:4` |
| Answer Correctness | Có | **Có** (trọng số 0.75/0.25) | `weights` — `third_party/GraphRAG-Benchmark/Evaluation/metrics/answer_accuracy.py:153` |
| Coverage | Có | Không | `compute_coverage_score` — `third_party/GraphRAG-Benchmark/Evaluation/metrics/coverage.py:63` |
| Faithfulness | Có | Không | `compute_faithfulness_score` — `third_party/GraphRAG-Benchmark/Evaluation/metrics/faithfulness.py:68` |

**Trỏ `--base_url` sang vLLM local được không?** **Có**, ở mode `API`:
`ChatOpenAI` nhận `base_url=args.base_url` (`ChatOpenAI` — `third_party/GraphRAG-Benchmark/Evaluation/retrieval_eval.py:139-152`);
script bắt buộc có `LLM_API_KEY` khác rỗng (`LLM_API_KEY` — `third_party/GraphRAG-Benchmark/Evaluation/retrieval_eval.py:130`), nên với vLLM
chỉ cần đặt một giá trị giả. Request có kèm `seed`, `top_p`, `presence_penalty`, `frequency_penalty`; việc vLLM chấp nhận đủ các tham số này là
**[UNVERIFIED — chưa chạy trong session]**. Lưu ý: mode `API` luôn nạp embedding:
`HuggingFaceBgeEmbeddings` — `third_party/GraphRAG-Benchmark/Evaluation/retrieval_eval.py:155`,
dù retrieval metrics **không dùng** embedding → tải BAAI/bge-large-en-v1.5 một cách không cần thiết (cỡ ~1,3 GB, **[UNVERIFIED]**).
Mode `ollama` dùng API native của Ollama, không dùng với vLLM được.

**Sai khác paper ↔ code (quan trọng khi trích dẫn).** Appendix F (Eq. 3, paper tr. 25) định nghĩa Context Relevance là
(1/|C|)·Σ_c R(c, Q, E), tức là **trung bình theo từng context và có dùng evidence E**. Code lại **nối mọi context** thành một chuỗi,
gọi LLM chấm 0–2 hai lần và **không dùng evidence**. §3.3 (paper tr. 7) còn mô tả metric này là "semantic similarity". Evidence Recall
(Eq. 4) thì khớp với code.

**Kết luận (a): Có — có điều kiện.** Ta chấm được một standalone evidence reranker trên **fixed candidate evidence pool**
mà **không cần rebuild GraphRAG index**: chỉ cần xuất top-k của reranker vào trường `context` (dạng list) kèm `evidence`, rồi chạy
`retrieval_eval.py` với judge là vLLM. Các điều kiện và giới hạn:
1. GraphRAG-Bench **không cung cấp pool** ứng viên cho từng câu hỏi (corpus là 20 tiểu thuyết + tài liệu y khoa). Phải tự tạo pool
   (chunk + BM25/dense top-N). Đây là bước first-stage retrieval, không phải GraphRAG index.
2. Retrieval metrics **không nhạy thứ tự**: mọi context được nối lại rồi cắt ở 20k ký tự. Chúng đo **chất lượng tập top-k**, không đo
   chất lượng xếp hạng → vẫn cần Recall@k/MRR/nDCG của riêng ta, mà các metric này cần nhãn passage-level (GraphRAG-Bench chỉ có
   chuỗi `evidence`).
3. Benchmark **không có conflict** → chỉ dùng làm kiểm tra **"no-harm"** (reranker conflict-aware có làm hỏng trường hợp không
   conflict không), tương tự thí nghiệm "golden" của TruthfulRAG (paper TruthfulRAG, Table 2, tr. 6).
4. Paper có baseline "RAG (w/ rerank)" dùng `bge-reranker-large`, `retrieval_topk: 5` (paper tr. 28–29) → có thể đối chiếu trực tiếp.

### (b) TruthfulRAG: `entropy_based_filter`

**Luồng gọi.** `run` → `make_knowledge_graph` → `knowledge_graph_retrieve` → `entropy_based_filter(sample, elements[:30], threshold=self.threshold)`
→ giữ `[:10]` → `get_predictions` (CoT):
- `elements` — `third_party/TruthfulRAG/truthfulrag/pipeline.py:412-413`
- Ablation "w/o KG": lọc trên **câu của raw context** — `split_by_sentence` — `third_party/TruthfulRAG/truthfulrag/pipeline.py:517-519`

**Công thức (code).** Với câu hỏi q và mỗi element e (chuỗi path hoặc câu):
1. `max_tokens` = số token tiktoken của **gold answer** — `max_tokens` — `third_party/TruthfulRAG/truthfulrag/modules.py:382` (HF: `max_new_tokens` dòng 385; `max_new_tokens` — `third_party/TruthfulRAG/truthfulrag/llm/backend.py:174`).
2. LLM sinh greedy (temperature 1e-6) với `logprobs=True`, `top_logprobs=10` — `top_logprobs` — `third_party/TruthfulRAG/truthfulrag/llm/backend.py:161-163`.
3. Tại mỗi vị trí t: p_i = exp(ℓ_i)/Σ_j exp(ℓ_j) trên **top-10**, H_t = −Σ_i p_i·ln(p_i + 1e−10); H = trung bình H_t theo các vị trí
   — `entropy_list` — `third_party/TruthfulRAG/truthfulrag/llm/backend.py:183-191` (**log tự nhiên**).
4. `baseline_entropy` = H(q, ∅) **không có fact** — `baseline_entropy` — `third_party/TruthfulRAG/truthfulrag/modules.py:404-409`.
5. Với mỗi e: ΔH = H(q, e) − H(q, ∅) — `entropy_delta` — `third_party/TruthfulRAG/truthfulrag/modules.py:433`.
6. **Luật giữ (code)**: giữ e nếu ΔH ≥ 0; hoặc nếu ΔH < 0 và H(q,∅)/H(q,e) ≤ 10^τ
   — `entropy_delta` — `third_party/TruthfulRAG/truthfulrag/modules.py:435-444`.
   Nghĩa là **chỉ loại** những element làm entropy **giảm hơn 10^τ lần** (cộng thêm trường hợp H(q,e)=0 và ΔH<0).
7. Nếu không giữ được element nào thì lấy element có H(q,e) lớn nhất — `entropy_deltas_dict` — `third_party/TruthfulRAG/truthfulrag/modules.py:445-453`.
8. Xếp theo ΔH **giảm dần** (tăng entropy nhiều nhất lên đầu), lấy `top_k` — `heapq` — `third_party/TruthfulRAG/truthfulrag/modules.py:456`.

**Threshold.** Mặc định code τ = 1 (`threshold` — `third_party/TruthfulRAG/truthfulrag/pipeline.py:287`; README cũng dùng 1).
Paper: τ = 1 cho GPT-4o-mini và Mistral-7B-Instruct, τ = 3 cho Qwen2.5-7B-Instruct; chạy trên V100 32 GB, temperature 0, Top-K 10
[paper tr. 5, Implementation Details].

**LLM được gọi ở bước nào.** (i) dựng KG: trích entity/relation từng chunk (kèm gleaning); (ii) trích keyword từ câu hỏi; (iii) **lọc**:
1 lần cho baseline + 1 lần cho **mỗi** element (tối đa 30 theo `run`), tất cả đều cần logprobs; (iv) sinh câu trả lời CoT. Như vậy chi phí
của riêng bước lọc là **(N+1) lần gọi LLM có logprobs cho mỗi câu hỏi**.

**Sai khác paper ↔ code.** Paper (Eq. 9–11, tr. 4) dùng log₂ và luật **P_corrective = {p : ΔH_p > τ}**. Code dùng ln và luật tỉ lệ
10^τ như ở bước 6, giữ cả mọi element có ΔH ≥ 0 bất kể τ. Hai luật **không tương đương**.

**Giả định nền tảng (quan trọng cho đề tài).** Figure 2 (tr. 3) vẽ path "Supporting" và "Irrelevant" bị bỏ, chỉ giữ path "Conflicting"
(ΔH > τ). Related Work (tr. 7) ghi rõ họ theo "non-parametric knowledge preference paradigm". Dữ liệu cũng khớp với điều này: trong
`datas/*_negative.json`, trường `answer` **là đáp án counterfactual** (ví dụ "In what country is Normandy located?" → `Spain`), tức là
mục tiêu của họ là **trung thành với context**. Hệ quả cho ta: khi pool có **misinformation (genuine conflict)**, tiêu chí "giữ thứ làm tăng
uncertainty so với parametric knowledge" có thể **ưu tiên chính passage sai**. Đây là **suy luận từ công thức**, cần thí nghiệm để xác nhận.

**Có tách ra làm baseline filter được không? Có.** `entropy_filter(sample, elements, backend_type, model_name, top_k, threshold)` nhận
`elements` là list chuỗi tùy ý (ablation đã dùng câu của context), nên áp được trực tiếp lên **passage của fixed pool**. Điều kiện:
- `sample` cần `question`, `answer` (gold, chỉ dùng để lấy độ dài), tùy chọn `choices` (multiple choice).
- Để công bằng, phải **thay độ dài gold answer bằng `max_tokens` cố định** (ví dụ 16–32), nếu không sẽ rò rỉ thông tin gold.
- Backend phải trả về `logprobs`/`top_logprobs` (vLLM OpenAI server hỗ trợ logprobs; giới hạn `top_logprobs` cụ thể: **[UNVERIFIED]**).
- Phương án sạch nhất: port khoảng 40 dòng logic (Apache-2.0, ghi attribution), thay vì kéo theo `torch` / `sentence_transformers` của repo.

**File trong `truthfulrag/`**: `__init__.py`, `base.py`, `evaluate.py`, `modules.py`, `pipeline.py`, `prompts.py`, `utils.py`,
`kg/__init__.py`, `kg/nano_vector_db_impl.py`, `kg/networkx_impl.py`, `llm/__init__.py`, `llm/backend.py`, `llm/hf.py`, `llm/ollama.py`,
`llm/openai.py`, `util/__init__.py`, `util/format_util.py`, `util/logger.py` (18 file).

**File trong `datas/`** (đếm bằng script):

| File | n | Trường | Ghi chú |
|---|---|---|---|
| `faitheval_data.json` | 1.000 | id, question, answer, answerKey, choices(4), context, justification, num of options | FaithEval |
| `musique_golden.json` | 1.772 | question, choices(4), id, answer, context | context không conflict |
| `musique_negative.json` | 1.772 | như trên | context **đã sửa** + answer counterfactual (ví dụ Tamaulipas → Sinaloa) |
| `squad_golden.json` | 1.769 | question, choices(4), id, answer, context | |
| `squad_negative.json` | 1.769 | như trên | ví dụ France → Spain |
| `timeqa_2022_nota.json` | 113 | context, question, choices(5), answer, id | Figure 3 (tr. 6) dùng tên file này làm tiêu đề một panel; việc nó ứng với "RealtimeQA" trong Table 1 là **suy luận** (4 panel ↔ 4 dataset); ví dụ đầu có answer "I don't know" |

### (c) MAGIC và CONFLICTS: format và khả năng chuyển thành fixed pool

**MAGIC** (1.080 cặp; single-hop 208/154/80/50, multi-hop 300/158/80/50 cho số conflict 1/2/3/4 [paper tr. 4, 6]):
- Bản ghi: `id` (int), `rel_id` (Wikidata P-id), `subgraph` (list chuỗi "(h | r | t)"), `original_triplet` (string ở file `1-*`, list ở file `2..4-*`),
  `perturb_triplet` (list; multi-hop là list lồng), `context1` (text của graph gốc), `context2` (text đã perturb).
- **Không có question/answer.** Tác vụ gốc là phát hiện + định vị conflict giữa 2 context, chấm **thủ công** [paper tr. 6].
- Phân tích perturbation của `1-single-hop` (đếm bằng script): **149/208 (72%) là thay relation**, chủ yếu **phủ định** ("equivalent to" →
  "not equivalent to", "contains" → "does not contain") hoặc **đảo chiều** ("father" → "son", "student of" → "teacher of"); 59/208 là thay entity.
  Relation phổ biến gồm P460 (said to be the same as), P1889 (different from), P361 (part of), P150, P3179, P1382, tức là nhóm
  **identity / mereology**.
- Chuyển thành pool:
  - **Typing/detection (theo cặp)**: dùng trực tiếp được; mọi cặp là conflict **tường minh** → nhãn `genuine` (rất hợp để kiểm "typer
    không gán nhầm genuine thành apparent"). MAGIC **không có cặp apparent hay cặp không conflict** → phải tự sinh (synthetic).
  - **Reranking**: tạo câu hỏi từ `original_triplet` (h, r, ?) bằng template theo `rel_id`; pool = {context1 (`compatible`), context2
    (`contradicting`)} + context của item khác làm `irrelevant`. Khả thi với `1-single-hop`; với multi-hop thì đáp án không rõ ràng.
    Phần template là do ta thêm vào → phải ghi là dẫn xuất.

**CONFLICTS** (458 câu):
- Bản ghi: `source`, `question`, `search_results` (5–20 kết quả, median 9; mỗi kết quả có `title, url, snippet, date, response_str, short_text`),
  `conflict_type`, `correct_answer` (rỗng với loại complementary/opinion).
- Phân bố (đếm bằng script): No conflict 161, Complementary information 115, Conflicting opinions and research outcomes 115,
  Conflict due to outdated information 62, Conflict due to misinformation **5**. Nguồn: conflicting_qa 162, situated_qa_geo 105, freshqa 95, qacc 55, situated_qa_temp 41.
  `short_text` median 1.835 ký tự (max 2.541).
- **Nhãn ở mức query**, không có nhãn relevance hay conflict ở mức passage.
- Chuyển thành pool: **pool có sẵn** (`search_results` + `short_text`), nhưng để có Recall@k/FCFR phải **suy ra nhãn passage**: (i) khớp chuỗi
  `correct_answer` (nhiễu), (ii) LLM judge, hoặc (iii) gán nhãn tay cho một tập nhỏ (~50 query). Ánh xạ sang taxonomy của ta:
  Outdated ≈ `temporal_scope`; Complementary (câu hỏi underspecified; nhiều câu từ SituatedQA geo/temp) ≈ apparent (phạm vi/ngữ cảnh);
  Misinformation ≈ genuine (chỉ 5 câu → quá ít; paper typing tự tạo biến thể "planted false source" trên 96 query [Khatri et al., tr. 7, 9]);
  Conflicting opinions nằm ngoài phạm vi factual. Paper typing cũng ghi taxonomy coi khác biệt **granularity là "No conflict"** (tr. 3).
- Slice nhỏ: chỉ dùng `short_text` (~2 KB × ~9 đoạn ≈ 18 KB/query) → 200 query ≈ 3,7 MB; không commit vì là text web bên thứ ba.

**Kết luận (c).** MAGIC phù hợp làm **bộ kiểm genuine conflict tường minh** (theo cặp, có triple vàng), không phù hợp cho apparent conflict.
CONFLICTS cho **pool tự nhiên** cùng nhãn loại conflict ở mức query (tốt cho typing mức query và cho phân tích apparent conflict tự nhiên
kiểu outdated/complementary), nhưng cần gán thêm nhãn passage để đo reranking. Cả hai đều **chuyển được** nhưng phải thêm nhãn hoặc template.

### (d) Mở rộng ArbGraph thành bài journal (IEEE Access / PLOS ONE / Scientific Reports)?

**ArbGraph làm gì (từ code + paper).** Pipeline: Wikipedia API → atomic claims (LLM) → gộp claim (embedding ≥ 0.88 + kiểm lexical)
→ lọc theo query (τ_q = 0.3) → chọn cặp theo cosine → LLM gán `support/contradiction/neutral` → **trọng tài lặp**:
- Mỗi claim có logit = 0 (p = 0,5); mỗi vòng chọn tối đa `arbitration_budget`=3 cặp contradiction có cường độ (p_u+p_v)/(1+|p_u−p_v|) lớn nhất
  — `intensity` — `third_party/ArbGraph/conflict_arbitration.py:95-99`.
- LLM phân xử A/B/unknown kèm confidence (dùng tối đa 5 claim support làm ngữ cảnh) — `_resolve_pair` — `third_party/ArbGraph/conflict_arbitration.py:103-162`;
  chỉ cập nhật khi confidence ≥ 0,5 (`gate`): winner +η, loser −η với η = 0,8 — `_update` — `third_party/ArbGraph/conflict_arbitration.py:177-184`.
- Cuối cùng giữ claim có p ≥ 0,3 — `accept_threshold` — `third_party/ArbGraph/conflict_arbitration.py:205`. Hệ quả số học: thua 1 lần → p = σ(−0,8) ≈ 0,31
  (vẫn giữ); thua 2 lần → p ≈ 0,17 (bị suppress).
- Paper: LongFact + RAGChecker, backbone Qwen3-4B-Instruct và LLaMA-3.1-8B-Instruct [tr. 11–12]; future work: "temporal dependencies or causal
  relations", lightweight arbitrator, multimodal [tr. 20–21]. PDF dùng template ACM TOIS ("ACM Trans. Inf. Syst., Vol. 1, No. 1", DOI placeholder)
  [tr. 1] → có thể đang nhắm TOIS, **[UNVERIFIED]**.

**Điểm yếu / khe hở có thể khai thác (kiểm được bằng code).**
1. **Không có typing conflict**: mọi cạnh `contradiction` đều được đem ra phân xử thắng/thua (`_select_conflicts` — `third_party/ArbGraph/conflict_arbitration.py:77-99`).
   Apparent conflict (alias, granularity, temporal scope) mà LLM gán nhầm là contradiction thì một bên sẽ bị phạt → **over-filtering**.
   Chính case study của paper (tr. 19) là một apparent conflict: "U.S. joined EAS in 2011" và "skipped the 2017 meeting", cộng thêm một
   homonym (EAS = Emergency Alert System).
2. **Không có alias/entity linking**: `_is_mergeable` — `third_party/ArbGraph/claim_alignment.py:70-92` đòi phải có key term chung, nên "Saigon"
   và "Ho Chi Minh City" sẽ **không** được gộp.
3. **Khó tái lập**: thiếu dữ liệu LongFact trong repo; retrieval qua API Wikipedia "sống" (thay đổi theo thời gian); tham số code khác README (§3.5);
   `HFAdapter` không dùng chat template.
4. **Không có LICENSE** → không copy code; phải tự cài đặt lại từ paper (§2).

**Tiêu chí của ba venue** (kiểm qua WebSearch ngày 2026-11-02; trang gốc chưa mở được trong sandbox):
- **IEEE Access**: binary peer review (accept/reject), tối thiểu 2 reviewer; tiêu chí "original, technically correct, clearly presented, high interest";
  bài không thể hiện **tiến bộ rõ so với state of the art** có thể bị desk reject; APC 2.075 USD theo trang APC của IEEE
  ([Reviewer Guidelines](https://ieeeaccess.ieee.org/reviewers/reviewer-guidelines/), [APC](https://ieeeaccess.ieee.org/about/article-processing-charges/)).
  Con số APC: **[UNVERIFIED — lấy từ snippet tìm kiếm]**.
- **PLOS ONE**: đánh giá **technical rigor**, không xét "perceived novelty, impact, journal fit"; yêu cầu công bố dữ liệu
  ([Academic editor role](https://journals.plos.org/plosone/s/academic-editor-role)). APC: các nguồn thứ cấp mâu thuẫn nhau → **[UNVERIFIED]**.
- **Scientific Reports**: "scientifically valid and technically sound", không xét perceived importance (Wikipedia dẫn Guide to Referees:
  [Scientific Reports – Wikipedia](https://en.wikipedia.org/wiki/Scientific_Reports)). Trang gốc của journal: **[UNVERIFIED]**.

**Kết luận (d): Có điều kiện. Khả thi, nhưng không có gì bảo đảm được accept.** Một bài journal khả thi nếu được định vị **không phải là
"ArbGraph v2"** mà là một **module typed-arbitration / reranking tổng quát**, trong đó ArbGraph chỉ là một baseline. Cụ thể:
1. **Đóng góp kỹ thuật mới**: phân loại apparent vs. genuine **trước** khi phân xử, chỉ đưa cặp `genuine` vào trọng tài, còn cặp apparent thì
   "hợp nhất có chú thích" (alias, granularity, temporal scope) dựa trên KG schema. Đây là phần giao với G2 trong `03_candidate_gaps.md`.
2. **Đánh giá có kiểm soát** trên fixed candidate evidence pool đã đóng băng (thay cho API Wikipedia sống), có FCFR/over-filtering theo
   từng loại conflict, nhiều seed, kiểm định thống kê, cùng code và dữ liệu mở (bắt buộc với PLOS ONE).
3. **Phân tích chi phí trên 1× RTX 5090** (số lần gọi LLM/câu, độ trễ) làm điểm cộng thực tiễn.

Theo tiêu chí trên: **IEEE Access** đòi tiến bộ rõ so với state of the art, nên cần (1) cộng (2) với kết quả mạnh. **PLOS ONE / Scientific
Reports** chấm soundness hơn novelty, nên một **nghiên cứu thực nghiệm chặt chẽ** (kiểu G7, over-filtering của ArbGraph, TruthfulRAG và
LLM-judge filter) cũng phù hợp; đổi lại, hai venue này ít phổ biến trong cộng đồng NLP/IR. Nên kiểm quy định của khoa/lab về venue hợp lệ
cho luận án: **[UNVERIFIED]**.

Rủi ro: (i) nhóm tác giả gốc (RUC AI Box) đã tự nêu hướng "temporal dependencies" [tr. 20] → mở rộng theo trục temporal dễ bị **trùng hoặc
bị đi trước**; (ii) năm 2026 có nhiều công trình gần (EvoTrustRAG, HVM-GraphRAG, MemGraphRAG… — đã kiểm chứng ở `02b` §5);
(iii) license (không copy code); (iv) chi phí LLM theo số cặp claim (ước tính ở Phase C, `06`).

---

## 5. Các mục [UNVERIFIED] phát sinh ở Phase A (sẽ gom vào `07_uncertainties.md`)

1. License của dữ liệu đi kèm repo: corpus GraphRAG-Bench; HotpotQA, 2WikiMultiHopQA, MuSiQue, ConcurrentQA trong Relink.
2. Repo `RUCAIBox/ArbGraph` và license của nó; ArbGraph có đang submit ACM TOIS không.
3. vLLM có chấp nhận `seed / presence_penalty / frequency_penalty` từ `ChatOpenAI` không; giới hạn `top_logprobs`; có hỗ trợ OpenAI Batch API (cho kapipe) không.
4. Dung lượng thật của BAAI/bge-large-en-v1.5.
5. ~~Nội dung paper gốc CONFLICTS (Cattan et al. 2025)~~ → **đã đọc** (PDF attach sau Phase A; `02b` §5).
6. Tiêu chí và APC của IEEE Access / PLOS ONE / Scientific Reports — mới thấy qua snippet tìm kiếm.
7. ~~Các công trình 2026 chỉ thấy qua tìm kiếm~~ → EvoTrustRAG, HVM-GraphRAG, MemGraphRAG, ConflictRAG **đã đọc full text**; ConflictQA, T-GRAG,
   EvoReasoner **đã quét** qua arXiv (`02b`, `03`). **Còn lại**: TimeR4, Ragability, "When Facts Change" (aclanthology.org bị chặn), EvidenceConflict.
