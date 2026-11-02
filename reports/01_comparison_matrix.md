# 01 — Comparison matrix (Phase A)

> Nguồn: code tại các commit ở `02_codebase_map.md` §1; 10 PDF bạn attach (số trang = trang của file PDF);
> WebSearch ngày 2026-11-02 (luôn đánh dấu **[UNVERIFIED]** vì chưa đọc full text). Tài liệu này **không** chứa kết quả thí nghiệm nào của ta.
> Ký hiệu: ✅ = có và được vận hành hóa rõ (code hoặc định nghĩa); ◐ = một phần / chỉ nhắc tới; ✗ = không có; — = không áp dụng.

## 1. Danh mục nguồn

| # | Công trình | Venue / ID (như in trên PDF hoặc README) | Tác giả (đơn vị) | Code đã audit? |
|---|---|---|---|---|
| 1 | TruthfulRAG | AAAI 2026 (© AAAI 2026, tr. 1); arXiv 2511.10375v1 | Liu, Shang, Zhang (BUPT) | ✅ |
| 2 | GraphRAG-Bench ("When to use Graphs in RAG") | "Published as a conference paper at ICLR 2026"; arXiv 2506.05690v3 | Xiang, Wu, Zhang, Chen, Hong, Huang, Su (Xiamen U., PolyU) | ✅ |
| 3 | MAGIC | Findings of EMNLP 2025 (README; ACL Anthology 2025.findings-emnlp.466) | Lee, Lee, Kim (Hanyang U., KT) | ✅ (chỉ dữ liệu) |
| 4 | CONFLICTS ("DRAGged into CONFLICTS") | arXiv 2506.08500v2 (PDF đã attach sau Phase A) | Cattan, Jacovi, Ram, Herzig, Aharoni, Goldshtein, Ofek, Szpektor, Caciularu (**Google Research**, Bar-Ilan U.) | ✅ (chỉ dữ liệu) |
| 5 | "Do We Need an LLM to Know Why Sources Conflict?" (conflict typing bằng decision model) | arXiv 2610.36915v1 (27/10/2026) | Khatri, Jain, Kapoor, Sah (**Independent Researchers**) | ✅ (audit mở rộng, `02b` §4.2) |
| 6 | ArbGraph | arXiv 2604.18362v1; template ACM TOIS (Vol. 1 No. 1, DOI placeholder) | Niu, Wang, Ren, Fang, Zhao (Renmin U., CMU) | ✅ |
| 7 | Relink | AAAI 2026 (© AAAI 2026, tr. 1); arXiv 2601.07192v1 | Huang, Bu, He, Zhuo, Wu (HFUT, William & Mary) | ✅ |
| 8 | ProStruct-RAG | EMNLP 2026, pp. 6749–6771 (README kapipe: 2026.emnlp-main.294) | Nishida (AIST), **Cheng (Kyoto University, NII LLMC)**, Matsumoto (Tohoku U., RIKEN) | ✅ (kapipe) |
| 9 | ContextConflict | EMNLP 2026, pp. 21142–21169; arXiv 2609.03148 (README) | Yang, Liu, Li, Lei (Northwestern, NYU, U. Florida) | ✅ (audit mở rộng, `02b` §4.1; code steering **chưa công bố**; **không có license**) |
| 10 | PAGE-RAG | arXiv 2607.19301v1 | Chen, An, Guo, Wang (CUIT, Beihang) | ✅ (audit đợt 3, `02c` §3.4; Apache-2.0) |
| 11 | Knowledge Conflicts for LLMs: A Survey | arXiv 2403.08319v2 | Xu, Qi, Guo, Wang, Wang, Zhang, Xu (Tsinghua, Cambridge, Westlake, CUHK) | — |
| 12 | MemGraphRAG | KDD 2026 (header tr. 14; README); arXiv 2606.00610v1 | Wu, Xiang, Tang, Chen, Zhang, Su (Xiamen U., Jilin U.) | ✅ (audit mở rộng, `02b` §4.3; MIT) |
| 13 | HVM-GraphRAG | arXiv 2607.24861v1 | He, Wang, Fan, Li, Zhang, Chang, Wang (Jilin U., PolyU) | ✗ (PDF không có link code) |
| 14 | EvoTrustRAG | arXiv 2608.07933v1 [cs.CR] | Nie, Li, Wu, Fan, Song, Jiang (UESTC, CAS) | ✗ (PDF không có link code) |
| 15 | ConflictRAG | arXiv 2605.17301v2 | Wang, Li, Liu, Shu (Zhengzhou U., Taiyuan U. of Tech., Zhejiang U.) | ✗ (PDF không có link code) |
| 16 | When Facts Change | Findings of ACL 2026, pp. 2154–2184 | Wallat, Sikdar, Nejdl (L3S Research Center) | ✅ (`02c` §3.1; **không có license**) |
| 17 | Ragability | LREC 2026 | Gross, Petrak, Krenn (OFAI) | ✅ (`02c` §3.2; Apache-2.0; corpus CC-BY-SA-4.0) |
| 18 | TimeR4 | EMNLP 2024 | Qian, Zhang, Zhao, Zhou, Sui, Zhang, Song (Nankai U., Tiangong U.) | ✅ (`02c` §3.3; **không có license**) |

Lưu ý về tên file: PDF số 5 được đặt tên "Google_Research_CONFLICTS…", nhưng trang 1 ghi tác giả là **các nhà nghiên cứu độc lập**.
Paper này chỉ **xây dựng trên** benchmark CONFLICTS của Cattan et al. (repo `google-research-datasets/rag_conflicts`).

## 2. Ma trận A — tổng quan bài toán

| Công trình | Loại | Bài toán | Đơn vị evidence | Fixed candidate pool? | Graph / KG | Vai trò LLM |
|---|---|---|---|---|---|---|
| TruthfulRAG | method | QA trắc nghiệm dưới context–memory conflict | 1 context/ví dụ → path KG | ✗ (1 context) | KG dựng on-the-fly từ context (LightRAG-style) | trích KG, keyword, lọc entropy (logprobs), sinh đáp án |
| GraphRAG-Bench | benchmark | so sánh RAG và GraphRAG theo 4 mức độ khó | context do hệ thống trả về | ✗ (corpus thô) | đánh giá graph của framework khác | judge (relevance, recall, correctness…) |
| MAGIC | benchmark | phát hiện và định vị inter-context conflict | cặp context1/context2 | ◐ (cặp 2 đoạn) | Wikidata5M subgraph (offline) | sinh text từ graph (GPT-4o-mini) |
| CONFLICTS | benchmark | typing conflict mức query (5 lớp) + sinh câu trả lời | kết quả Google search (5–20/query) | ✅ (pool tự nhiên) | ✗ | (paper gốc: LLM typing; chưa đọc) |
| Khatri et al. 2026 | analysis | typing conflict bằng decision model, cascade sang LLM | như CONFLICTS | ✅ | ✗ | decision model / Gemini |
| ArbGraph | method | long-form RAG; trọng tài evidence trước khi sinh | atomic claim | ✗ (Wikipedia API sống) | evidence graph support/contradiction | tách claim, gán quan hệ, phân xử, sinh |
| Relink | method | multi-hop ODQA trên GraphRAG | triple/path | ✗ | KG (Neo4j) + latent relation pool | trích triple, chấm, suy luận |
| ProStruct-RAG | method | temporal QA trên tri thức tiến hóa / mâu thuẫn | proposition có timestamp | ✗ | proposition graph (updates/contradicts/supports) | trích proposition, gán quan hệ, QA |
| ContextConflict | benchmark + steering | resolve conflict trong context (6 loại) | evidence pieces (2,3–5,7/instance) | ◐ | ✗ | đối tượng đánh giá; steering activation |
| PAGE-RAG | method | GraphRAG trên tài liệu dài, có cơ chế abstain | span / graph node | ✗ | graph làm "semantic skeleton" | routing, sinh, abstain |
| Survey | survey | taxonomy CM / IC / IM conflict | — | — | — | — |

## 3. Ma trận B — xử lý conflict (trọng tâm Paper 3)

| Công trình | Khái niệm conflict | Mức typing | Tách apparent vs. genuine? | alias / historical name | granularity | temporal scope | homonym | related-but-different predicate |
|---|---|---|---|---|---|---|---|---|
| TruthfulRAG | external vs. parametric (ΔH entropy) | ✗ | ✗ (mặc định tin external: "non-parametric knowledge preference", tr. 7) | ✗ (gộp node theo tên in hoa) | ✗ | ◐ (có RealtimeQA, không mô hình hóa thời gian) | ✗ | ✗ |
| GraphRAG-Bench | — | — | — | — | — | — | — | — |
| MAGIC | inter-context, sinh từ KG | theo cặp (ID/LOC) | ✗ (mọi cặp đều là conflict) | ◐ (P460/P1889 bị **phủ định** → genuine) | ◐ (P361/P150 bị phủ định/thay → genuine) | ✗ | ✗ | ◐ (thay relation, chủ yếu phủ định/đảo chiều) |
| CONFLICTS + Khatri et al. | inter-context, nguyên nhân bất đồng | **query** (5 lớp) | ◐ (No conflict / Complementary / Outdated so với Misinformation / Opinions) | ✗ | ◐ (gộp vào "No conflict", Khatri tr. 3) | ✅ ("Outdated information") | ◐ (Complementary ⊃ câu hỏi underspecified, SituatedQA-geo) | ✗ |
| ContextConflict | trong context, 6 loại | instance | ◐ (granularity/ambiguity/perspective được xem là "nhiều đáp án hợp lệ" → summarization) | ✗ | ✅ (y khoa, ABSA) | ✅ (ConflictBank, CONFLICTS) | ✅ ("ambiguity", từ AmbigDocs) | ✗ |
| ArbGraph | claim–claim contradiction | ✗ (support / contradiction / neutral) | ✗ | ✗ (code) | ✗ | ✗ (future work, tr. 20) | ◐ (chỉ trong case study, tr. 19) | ✗ |
| Relink | "distractor facts" | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ◐ (ví dụ *died in* vs. *buried in*, tr. 1–2; xử lý bằng scorer đã học) |
| ProStruct-RAG | quan hệ proposition | cặp (updates / contradicts / supports / NOREL) | ✅ **trên trục thời gian** (updates = apparent, contradicts = genuine) | ✗ | ✗ | ✅ (timestamp = ngày xuất bản) | ✗ | ✗ |
| PAGE-RAG | — (độ tin cậy, abstain) | — | — | — | — | — | — | — |
| Survey | CM / IC / IM; nguyên nhân misinformation, outdated | khái niệm | ◐ | ✗ | ✗ | ◐ | ✗ | ✗ |
| MemGraphRAG | triple–triple lúc **dựng graph** (prompt LLM, ngưỡng confidence 0.85) | cặp triple cùng (subject, relation) | ✅ **ở mức prompt LLM**: mutual = genuine, granularity = tương thích, temporal phụ thuộc thời gian; LLM tự phán predicate uniqueness | ◐ (synonym edge theo embedding, không có thời gian hiệu lực) | ✅ (LLM phán containment, ví dụ city–country) | ✅ (LLM phán thời gian chồng lấn) | ✗ | ✗ |
| HVM-GraphRAG | như MemGraphRAG, cho tài liệu đa phương thức | nhóm triple | ✅ (cùng taxonomy, prompt ở appendix) | ✗ | ✅ (containment/hypernymy) | ✅ | ✗ | ✗ |
| EvoTrustRAG | nguồn gốc conflict: evolution / intervention / unresolved | nhóm fact span-grounded | ◐ (evolution ≈ apparent theo thời gian; intervention ≈ genuine/tấn công) | ✗ | ✗ | ✅ | ✗ | ✗ |
| ConflictRAG | no-conflict / factual / temporal / opinion | cặp tài liệu (MLP + LLM) | ◐ | ✗ | ✗ | ✅ | ✗ | ✗ |

| When Facts Change | context–parameter, fact **mutable vs. stable** | mức câu hỏi (1 context) | ◐ (mutability là manh mối apparent/genuine, nhưng LLM không dùng) | ✗ | ✗ | ✅ (mutable fact, document date) | ✗ | ✗ |
| Ragability | inter-context cần implicit reasoning (categorical / numerical / temporal) | cặp hoặc bộ 4 context (yes/no + nội dung) | ◐ (có control "không mâu thuẫn"; đo được false alarm khi có hint) | ✗ | ✗ | ◐ (tag temporal) | ✗ | ✗ |
| TimeR4 | không có conflict; rerank theo ràng buộc thời gian của câu hỏi | fact TKG | ✗ | ✗ | ✗ | ✅ (time constraint) | ✗ | ✗ |
| PAGE-RAG | không typing conflict; làm sạch graph bằng domain/range + type | node / edge | ✗ | ◐ (bảo vệ alias trùng tên) | ✗ | ✗ | ◐ (gộp chỉ khi cùng type) | ✗ |

Bốn dòng MemGraphRAG / HVM / EvoTrustRAG / ConflictRAG đã được **kiểm chứng bằng full text** (và code, riêng MemGraphRAG) ở `02b_extension_audit.md`
§4.3, §5; bốn dòng sau cùng ở `02c_extension_audit_2.md`.
Hệ quả: taxonomy "granularity tương thích / temporal / mutual" **không còn là điểm mới**; xem phần đánh giá lại G2 trong `03`.

## 4. Ma trận C — kỹ thuật và khả năng reuse

| Repo | License | LLM backend / vLLM | GPU / hạ tầng | Dữ liệu dùng được ngay | Reuse đề xuất cho Paper 3 |
|---|---|---|---|---|---|
| TruthfulRAG | Apache-2.0 | `openai` (đọc `OPENAI_BASE_URL` → vLLM ✅), `hf`, `ollama` | torch + sentence-transformers; paper chạy V100 32 GB | `datas/` (1 context/ví dụ; có bộ counterfactual) | **Baseline filter** (port `entropy_filter`, thay độ dài gold answer bằng `max_tokens` cố định) |
| GraphRAG-Bench | MIT | judge qua `ChatOpenAI(base_url=…)` → vLLM ✅ | LLM judge + bge embedding | 4.072 câu hỏi + corpus, **không có pool** | **Evaluator** cho tập top-k; kiểm "no-harm" khi không có conflict |
| MAGIC | CC-BY-4.0 | — | — | 1.080 cặp context có triple vàng | **Stress test genuine conflict** (typing theo cặp) |
| CONFLICTS | Apache-2.0 (file); text web bên thứ ba | — | — | 458 query + pool tự nhiên | **Pool tự nhiên**; typing mức query; phân tích outdated/complementary |
| ArbGraph | **không có** | HF local (mặc định Qwen3-4B-Instruct-2507) | GPU khuyến nghị (readme dòng 73) | ✗ (LongFact không kèm) | **Baseline** trọng tài: cài đặt lại từ paper, không copy code |
| Relink | MIT | OpenAI client với `base_url` → vLLM ✅; embedding mặc định là API trả phí | Neo4j + Redis + path scorer đã train | 500 mẫu 2WikiMultiHopQA (có `evidences` triple), HotpotQA, MuSiQue… | **Nguồn dữ liệu** (slice 2Wiki); ý tưởng predicate-distractor; không dùng làm baseline trực tiếp (quá nặng) |
| kapipe | Apache-2.0 | `OpenAI()` theo env → vLLM ✅ cho `generate`; Batch API ? | GPU cho model HF | nhiều script tiền xử lý dataset | **Thư viện**: BM25/Contriever, entity disambiguation (BLINK), docRE, relation extractor của ProStruct (baseline typing temporal), metric ranking |
| MemGraphRAG | MIT (code kế thừa HippoRAG) | `CacheOpenAI(base_url=…)` → vLLM ✅; pin `vllm==0.6.6.post1`, `torch==2.5.1` (RTX 5090: **[UNVERIFIED]**) | LLM cho OpenIE + schema + detect/resolve; embedding bge-large | không có pool; corpus HotpotQA/2Wiki/MuSiQue theo paper | **Baseline LLM-typer** (prompt `conflict_detection`); module conflict cắm vào được |
| ContextConflict | **không có license** (cả repo lẫn HF card) | `AsyncOpenAI(base_url=…)` → vLLM ✅; steering cần HF hook (không qua vLLM) | 8B–20B cho phân tích/steering | 5.781 mẫu; ambiguity (≈ homonym), temporal, misinformation (nhãn theo source) | **Dữ liệu đánh giá** (sau khi xin phép); steering **không có code** |
| decision-models typing | Apache-2.0 | Vercel AI Gateway viết cứng (**trả phí**) | CPU để phân tích lại output đã lưu | output 13 hệ trên CONFLICTS (dev/test cố định), `plants.json` | **Khung đánh giá** (split, metric, `plant`, cascade); typer local phải tự cài |

## 5. Nhận định chính

1. **Chưa thấy KG-schema typing để rerank** trong 10 repo đã audit. Typing hiện có thuộc các dạng: (i) **mức query** bằng LLM hoặc decision model
   (CONFLICTS, Khatri et al.); (ii) **theo cặp trên trục thời gian** bằng LLM (ProStruct-RAG); (iii) **benchmark** theo loại, đánh giá bằng
   summarization (ContextConflict); (iv) **prompt LLM mutual/temporal/granularity lúc dựng graph** (MemGraphRAG, HVM-GraphRAG; đã kiểm). Không cái
   nào dùng alias table có thời gian hiệu lực, hierarchy P131/P361, qualifier P580/P582, ràng buộc single-value hay type P31 làm **bằng chứng kiểm
   chứng được**, và không cái nào rerank fixed pool theo loại conflict.
2. **Các filter conflict đã audit đều "mù" với apparent conflict hoặc dựa vào phán đoán LLM**: entropy filter của TruthfulRAG, trọng tài của
   ArbGraph và scorer của Relink không có nhánh "conflict này chỉ là bề ngoài"; MemGraphRAG/HVM có nhánh đó nhưng không đo độ chính xác. Chưa ai
   đo over-filtering ở **mức passage theo từng loại apparent**; metric gần nhất là **WFR mức query** của EvoTrustRAG (đã kiểm).
3. **Các giả định trái ngược nhau**: TruthfulRAG tin external context (bộ `*_negative` lấy đáp án counterfactual làm gold), ArbGraph tin
   consensus/credibility, còn CONFLICTS tùy loại conflict. Paper 3 cần một setting có **cả misinformation lẫn apparent conflict** để so sánh công bằng.
4. **Dữ liệu cho prototype đã có sẵn trong repo**: 2WikiMultiHopQA (Relink, có triple → hợp với KG), CONFLICTS (pool tự nhiên), MAGIC (genuine
   tường minh), bộ counterfactual của TruthfulRAG. License của từng bộ phải kiểm trước khi dùng (`07`).
5. **Evaluator**: retrieval eval của GraphRAG-Bench chạy được với judge là vLLM nhưng **không nhạy thứ tự**; metric ranking cần tự cài
   (hoặc tham chiếu `kapipe/evaluation`).
