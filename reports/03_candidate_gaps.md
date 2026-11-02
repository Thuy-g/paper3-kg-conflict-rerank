# 03 — Candidate research gaps (Phase A)

> Mục đích: liệt kê 5 hướng (G2, G7, G1, G2+G1, G3+G8) kèm **bằng chứng** cho thấy chúng còn mở và **điều kiện làm chúng mất novelty**.
> Xếp hạng cuối cùng thuộc Phase C (`04_ranked_recommendation.md`). Mọi ngưỡng số trong phần "minimal falsifiable experiment" là
> **đề xuất để bạn chốt trước khi chạy (pre-registration)**, không phải kết quả.
> Mức bằng chứng: **[code]** đọc trực tiếp; **[paper tr. X]** PDF bạn attach; **[data]** đếm bằng script trên dữ liệu trong `third_party/`;
> **[search, UNVERIFIED]** chỉ thấy qua snippet WebSearch ngày 2026-11-02.

## 0. Định nghĩa dùng chung

- **Apparent conflict**: hai passage có vẻ mâu thuẫn nhưng tương thích khi xét tri thức KG:
  `alias` (kể cả historical name: Edo ↔ Tokyo), `granularity` (Kyoto ⊂ Japan qua P131/P361-like; cả granularity thời gian: "1990" so với
  "3/3/1990"), `temporal_scope` (đúng ở các khoảng thời gian khác nhau, qualifier P580/P582-like), `homonym` (cùng tên, khác entity,
  khác type P31-like), `predicate_mismatch` (quan hệ liên quan nhưng khác, ví dụ *place of birth* so với *place of death*).
- **Genuine conflict**: cùng entity, cùng predicate (functional), cùng khoảng thời gian, giá trị không thể dung hòa (counterfactual,
  misinformation, phủ định, đảo chiều quan hệ).
- **FCFR@k** (False Conflict Filtering Rate) = tỉ lệ passage có nhãn `compatible` bị đẩy ra khỏi top-k hoặc bị filter loại bỏ
  (định nghĩa của bạn), báo cáo kèm phân rã theo `conflict_type`. Đi cặp với **GER@k** (Genuine Exclusion Rate, đề xuất) = tỉ lệ passage
  `contradicting` nằm ngoài top-k. Một phương pháp tốt phải có FCFR thấp **và** GER cao.
- **Setting**: fixed candidate evidence pool; mọi phương pháp xếp hạng hoặc lọc **cùng một pool** cho mỗi câu hỏi.

## 1. Bằng chứng nền dùng chung cho nhiều gap

| # | Bằng chứng | Nguồn |
|---|---|---|
| E1 | ArbGraph chỉ có 3 nhãn quan hệ support / contradiction / neutral | `_verify_relation` — `third_party/ArbGraph/evidence_graph.py:157-173` [code] |
| E2 | ArbGraph đưa **mọi** cạnh contradiction vào phân xử thắng/thua, không xét loại | `_select_conflicts` — `third_party/ArbGraph/conflict_arbitration.py:77-99` [code] |
| E3 | ArbGraph gộp claim theo embedding ≥ 0,88 + bắt buộc có key term chung → alias không được gộp | `_is_mergeable` — `third_party/ArbGraph/claim_alignment.py:70-92` [code] |
| E4 | Tác giả ArbGraph tự nêu future work: "temporal dependencies or causal relations" | [paper ArbGraph tr. 20] |
| E5 | Case study của chính ArbGraph là apparent conflict ("joined 2011" và "skipped 2017") + homonym (EAS) | [paper ArbGraph tr. 19] |
| E6 | TruthfulRAG gộp node theo tên in hoa; chỉ 4 entity type; không xử lý alias/thời gian/hierarchy | `_handle_single_entity_extraction` — `third_party/TruthfulRAG/truthfulrag/modules.py:664-682`; `DEFAULT_ENTITY_TYPES` — `third_party/TruthfulRAG/truthfulrag/prompts.py:18` [code] |
| E7 | Entropy filter của TruthfulRAG giữ/loại theo ΔH, không theo tính tương thích; paper bỏ cả path "Supporting" | `entropy_delta` — `third_party/TruthfulRAG/truthfulrag/modules.py:435-444` [code]; Figure 2 [paper TruthfulRAG tr. 3] |
| E8 | TruthfulRAG giả định external knowledge đúng ("non-parametric knowledge preference") | [paper TruthfulRAG tr. 7] |
| E9 | ProStruct-RAG phân biệt updates vs. contradicts **chỉ** bằng timestamp; không có alias/granularity | `updates` — `third_party/kapipe/kapipe/proposition_relation_extraction/prompt_templates/prostruct_rag_proposition_relation_extraction_01.txt:13-14` [code]; [paper ProStruct tr. 3–4] |
| E10 | Taxonomy CONFLICTS gộp khác biệt granularity vào "No conflict"; typing ở **mức query** | [Khatri et al. tr. 3] |
| E11 | ContextConflict đánh giá granularity/ambiguity bằng summarization (Balance score), không lọc/xếp hạng; không có loại alias | [paper ContextConflict tr. 2–3] |
| E12 | CONFLICTS: 177/458 query (38,6%) là Complementary hoặc Outdated (bất đồng nhưng không sai); Misinformation chỉ 5 (1,1%) | [data] |
| E13 | MAGIC `1-single-hop`: 149/208 perturbation là thay relation (phần lớn phủ định / đảo chiều) → genuine tường minh, không có apparent | [data] |
| E14 | Slice 2WikiMultiHopQA trong Relink: 500 câu × 10 đoạn, có `evidences` triple; relation phổ biến: director, date/place of birth/death, country of citizenship | [data] |
| E15 | Relink coi *died in* so với *buried in* là "distractor fact" (liên quan nhưng lệch mục tiêu) | [paper Relink tr. 1–2] |

---

## G2 — KG-schema-aware apparent vs. genuine conflict typing → reranking

1. **Unresolved problem.** Trên fixed pool, các hệ thống hiện có hoặc coi mọi bất đồng là contradiction (ArbGraph: E1, E2), hoặc typing ở
   mức query (CONFLICTS: E10), hoặc typing theo cặp nhưng chỉ trên trục thời gian (ProStruct: E9). Chưa có cơ chế dùng **KG schema**
   (alias có thời gian hiệu lực, hierarchy located-in/part-of, qualifier start/end, type P31-like, cặp predicate tương thích) để phân loại
   **từng passage hoặc cặp passage** thành apparent hay genuine, kèm **KG facts làm lời giải thích**, rồi dùng nhãn đó để rerank sao cho
   **chỉ phạt genuine**.
2. **Closest methods.** ProStruct-RAG (LLM typing updates/contradicts theo cặp proposition); CONFLICTS + Khatri et al. (typing 5 lớp mức query);
   ContextConflict (benchmark có granularity/temporal/ambiguity); ArbGraph (contradiction + trọng tài, không typing); MAGIC (conflict sinh từ KG,
   chỉ detection); **[search, UNVERIFIED]** HVM-GraphRAG (arXiv 2607.24861) và MemGraphRAG (arXiv 2606.00610) phân loại
   mutual/temporal/granularity bằng prompt LLM; EvoTrustRAG (arXiv 2608.07933) phân loại nguồn gốc conflict (evolution / intervention / unresolved).
3. **Bằng chứng còn mở.** E1–E3, E6, E9–E11 (không repo nào đã audit làm KG-schema typing để rerank); E5 (chính ArbGraph gặp apparent conflict);
   E12 (apparent conflict theo nghĩa rộng **không hiếm** trong pool tự nhiên: 38,6% query CONFLICTS).
4. **Contribution.** (i) `ConflictTyper` dựa trên KG schema (rule-based, CPU, trả về `{type, evidence: [KG facts], confidence}`; LLM chỉ là
   fallback); (ii) `ConflictAwareReranker` = relevance − λ·penalty, **chỉ** phạt `genuine`; (iii) giao thức perturbation có kiểm soát cho 5 loại
   apparent + counterfactual với nhãn suy ra từ KG; (iv) đo FCFR/GER so với các filter hiện có.
5. **GPU/API.** Typing: CPU. Entity linking và triple extraction: có thể dùng LLM 7–8B qua vLLM (vừa 1× RTX 5090), hoặc **không cần LLM** nếu dùng
   triple có sẵn (2Wiki `evidences`, E14). Không cần API trả phí.
6. **Minimal falsifiable experiment.** 200–300 câu 2Wiki, pool 10 đoạn gốc + 6 đoạn chèn (1 cho mỗi loại: counterfactual, alias, granularity,
   temporal, homonym, predicate), seed cố định. So sánh BM25, cross-encoder, LLM-judge contradiction filter (prompt kiểu ArbGraph, cài lại),
   entropy filter (port TruthfulRAG), prompt LLM có typing (kiểu mutual/temporal/granularity), và KG-typed reranker.
   **H-G2**: KG-typed reranker giảm FCFR@5 ít nhất **10 điểm %** so với filter tốt nhất trong nhóm LLM, với GER@5 không thấp hơn quá **2 điểm %**.
   **Bác bỏ** nếu không đạt; hoặc nếu prompt LLM có typing đạt macro-F1 typing chênh không quá 2 điểm % với chi phí tương đương (khi đó đóng góp
   chỉ còn ở chi phí và khả năng giải thích).
7. **Điều gì làm mất novelty.** (a) Full text của HVM-GraphRAG / MemGraphRAG / EvoTrustRAG cho thấy họ đã dùng **KG schema** (không chỉ prompt) và
   áp vào **reranking/filter** trên pool cố định; (b) prompt LLM có typing ngang bằng KG typing; (c) apparent conflict hiếm trong pool **tự nhiên**
   ở mức passage (E12 chỉ là mức query, cần kiểm thêm); (d) một bài 2026 khác dùng chính alias/qualifier của Wikidata cho conflict trong RAG
   (chưa thấy, cần tìm có hệ thống ở Phase C).

## G7 — Empirical study về over-filtering

1. **Unresolved problem.** Các cơ chế lọc conflict (entropy-based, arbitration, LLM-judge, self-reflection) có thể **loại nhầm evidence
   tương thích** (alias, granularity, temporal). Chi phí của "false conflict" hầu như không được đo: các paper báo cáo accuracy cuối, CPR,
   FR/ID/Noise, chứ không có tỉ lệ evidence đúng bị loại theo từng loại apparent.
2. **Closest methods.** TruthfulRAG (ACC/CPR, Table 3 [paper tr. 7]); ArbGraph (FR, ID, Noise-S/I, Hallu., Faith. [paper tr. 11, 14]; độ chính xác
   từng component trên 200/50 mẫu, Table 4 [tr. 19]); Khatri et al. (planted false source: hit vs. false alarm **mức query**, Table 7 [tr. 9]);
   MAGIC ghi nhận LLM "over-detection" [paper MAGIC tr. 7]; **[search, UNVERIFIED]** EvoTrustRAG có thể báo cáo "wrong-filtering rate";
   ConflictRAG (arXiv 2605.17301) ghi nhận filter self-reflection loại cả evidence mâu thuẫn.
3. **Bằng chứng còn mở.** E2 và luật suppress của ArbGraph không xét loại conflict (thua 2 lần → p ≈ 0,17 < 0,3):
   `accept_threshold` — `third_party/ArbGraph/conflict_arbitration.py:205`; E7, E8 (TruthfulRAG loại theo ΔH và giả định tin external);
   chưa paper nào trong 10 PDF báo cáo FCFR theo loại apparent ở mức passage.
4. **Contribution.** Bộ đánh giá chuẩn hóa (FCFR@k, GER@k, phân rã theo loại) + phân tích có kiểm soát trên ≥ 3 filter đại diện, 2 nguồn pool
   (2Wiki có perturbation, CONFLICTS tự nhiên), nhiều seed, kiểm định thống kê. Dạng **analysis paper**, hợp tiêu chí "soundness" của
   PLOS ONE / Scientific Reports (xem câu (d) ở `02`).
5. **GPU/API.** Entropy filter cần (N+1) lần gọi có logprobs cho mỗi câu (N ≈ 10–16 passage); trọng tài kiểu ArbGraph cần O(#cặp) lần gọi.
   Tất cả chạy được với 7–8B trên vLLM, 1× RTX 5090; không cần API trả phí. Ước tính số lần gọi chi tiết ở Phase C (`06`).
6. **Minimal falsifiable experiment.** Cùng pool như G2. **H-G7**: với ít nhất 2 trong 3 filter (entropy, arbitration, LLM-judge), FCFR@5 trên
   passage apparent **cao hơn có ý nghĩa** so với passage gold không bị perturb (paired bootstrap hoặc McNemar, p < 0,05).
   **Bác bỏ** nếu không filter nào cho thấy khoảng cách này, tức là over-filtering không đáng kể.
7. **Điều gì làm mất novelty.** EvoTrustRAG (hoặc paper khác) đã có metric tương đương FCFR **theo loại apparent**; hoặc kết quả là "không có
   over-filtering", khi đó vẫn publish được dưới dạng negative result (hợp với PLOS ONE) nhưng không còn là động lực cho G2.

## G1 — KG-consistency reranker training-free

1. **Unresolved problem.** Rerank passage theo mức **nhất quán với KG** (support/contradict ở mức triple) mà không cần train, khác với
   scorer đã học của Relink.
2. **Closest methods.** Relink (PathScorer neural cần train + Neo4j); TruthfulRAG (Ref(p) dựa trên độ phủ entity/relation, Eq. 4–5
   [paper tr. 2–3]); GraphRAG-Bench (baseline `bge-reranker-large` [paper tr. 29]); **[search, UNVERIFIED]** TimeR4 (EMNLP 2024) rerank theo ràng buộc
   thời gian trên temporal KG. Các reranker "KG-enhanced" khác (ví dụ KG-FiD, KG-Rank): **[UNVERIFIED]**, chưa kiểm trong session.
3. **Bằng chứng còn mở.** `PathScorer` — `third_party/Relink/app/path_scorer.py:322` cần train và trọng số tải ngoài [code, README Relink];
   Ref(p) của TruthfulRAG đo độ phủ, không đo nhất quán.
4. **Contribution.** s(p) = rel(p) + α·support_KG(p) − β·contradict_KG(p), không train, dùng entity linking + triple extraction.
5. **GPU/API.** CPU (+ LLM extraction tùy chọn); không cần API trả phí.
6. **Minimal falsifiable experiment.** 2Wiki + counterfactual. **H-G1**: nDCG@5 hơn cross-encoder ít nhất **3 điểm** khi KG chỉ chứa **schema**
   (type, alias, hierarchy), **không** chứa fact của relation đang hỏi. **Bác bỏ** nếu lợi thế chỉ xuất hiện khi KG chứa chính đáp án (rò rỉ:
   2Wiki được dựng từ Wikidata, nên `evidences` chính là fact trả lời câu hỏi).
7. **Điều gì làm mất novelty.** Novelty risk **cao**: "KG-enhanced reranking" là chủ đề cũ. Nếu đóng góp chỉ là cộng điểm nhất quán KG thì khó
   bảo vệ; và nếu KG bao phủ đáp án thì câu hỏi "vì sao còn cần retrieval?" sẽ bị reviewer đặt ra.

## G2+G1 — Typed consistency reranking (ứng viên trung tâm cho tiêu đề "Relation-Aware")

1. **Unresolved problem.** Tín hiệu "không nhất quán với KG" của G1 bao gồm cả apparent conflict → G1 đơn thuần sẽ **phạt nhầm** alias,
   granularity, temporal. Cần dùng typing (G2) để quyết định tín hiệu nào là genuine.
2. **Closest methods.** Như G1 và G2; ArbGraph là baseline "consistency qua contradiction graph" gần nhất (không typing, E1–E2).
3. **Bằng chứng còn mở.** E1–E3, E6, E9 (không có hệ nào kết hợp typing với nhất quán KG); E5 (ArbGraph gặp đúng tình huống này).
4. **Contribution.** score = rel + α·support − β·1[type = genuine]·contradict, cộng thêm "hợp nhất có chú thích" cho apparent (ví dụ ghép
   "Edo (former name of Tokyo, until 1868)" vào lời giải thích). Có ablation đầy đủ: G1 đơn, G2 đơn, G2+G1, có và không có LLM fallback.
5. **GPU/API.** Như G2.
6. **Minimal falsifiable experiment.** **H-G2+G1**: G2+G1 có FCFR@5 thấp hơn G1 đơn ít nhất **10 điểm %**, GER@5 không thấp hơn quá **2 điểm %**,
   và EM/F1 downstream (generator cố định, 7–8B) không giảm. **Bác bỏ** nếu G1 đơn đã có FCFR thấp (khi đó typing không cần thiết) hoặc nếu
   EM/F1 giảm.
7. **Điều gì làm mất novelty.** Như G2 (đặc biệt là full text của HVM-GraphRAG, MemGraphRAG, EvoTrustRAG) cộng rủi ro của G1.

## G3+G8 — Temporal / cross-lingual alias

1. **Unresolved problem.** Historical name (Edo → Tokyo năm 1868, Bombay → Mumbai năm 1995, Saigon → Ho Chi Minh City năm 1976 — kiến thức
   phổ thông, **cần đối chiếu Wikidata**, hiện bị chặn) và tên đa ngôn ngữ (東京 / Tokyo, Sài Gòn / Saigon) tạo ra apparent conflict **phụ thuộc
   thời gian**: một tên chỉ hợp lệ trong một khoảng. Cần **alias resolution có thời gian hiệu lực** và đa ngôn ngữ.
2. **Closest methods.** ProStruct-RAG (timestamp, không alias: E9); MAGIC (perturb P460 "said to be the same as" như genuine conflict, E13);
   **[search, UNVERIFIED]** một paper temporal-KG cho rằng tên như "Oscar Awards" chỉ rõ nghĩa khi gắn với biến thể lịch sử (arXiv 2509.15464?);
   T-GRAG (arXiv 2508.01680); TimeR4. Entity disambiguation có sẵn trong kapipe (BLINK, LLMED) nhưng không có thời gian hiệu lực của alias.
3. **Bằng chứng còn mở.** E3, E6 (không repo nào xử lý alias); trong 10 PDF không có benchmark nào về false conflict do historical name;
   WebSearch cũng không tìm thấy benchmark như vậy (**[search, UNVERIFIED]**, cần tìm kỹ hơn).
4. **Contribution.** Bảng alias có `valid_from`/`valid_to` và đa ngôn ngữ (Wikidata labels/aliases + official name có qualifier — mã property
   cụ thể **[UNVERIFIED]**); một tập nhỏ có kiểm soát về apparent conflict do đổi tên; đo false-conflict rate của các filter. Hướng này có lợi thế
   ngôn ngữ (Nhật, Việt) cho nghiên cứu sinh ở Kyoto University.
5. **GPU/API.** Cần một subset Wikidata (tải trên máy local, kích thước cần ước tính); LLM đa ngôn ngữ 7–8B qua vLLM; không cần API trả phí.
6. **Minimal falsifiable experiment.** 100–200 item (câu hỏi + pool) có đáp án là entity từng đổi tên hoặc có tên đa ngôn ngữ.
   **H-G3**: LLM-judge filter 7–8B gán nhầm "conflict" cho ít nhất **20%** passage chỉ khác ở historical/cross-lingual alias, và alias table có thời
   gian hiệu lực giảm tỉ lệ này xuống ≤ **5%**. **Bác bỏ** nếu LLM 7–8B đã xử lý tốt (false conflict < 5% ngay từ đầu).
7. **Điều gì làm mất novelty.** LLM hiện đại đã nhận ra alias phổ biến (rất có thể với tên nổi tiếng như Tokyo/Edo); khi đó phải chuyển sang tên
   ít phổ biến (long-tail), làm giảm tính thực tế. Ngoài ra là các công trình temporal-KG 2025–2026 chưa đọc (**[UNVERIFIED]**).

---

## 2. So sánh sơ bộ (không phải xếp hạng cuối cùng; xếp hạng ở `04`, Phase C)

| Gap | Novelty risk | Tính khả thi trên 1× RTX 5090 | Thời gian tới kết quả đầu tiên (ước đoán) | Ghi chú |
|---|---|---|---|---|
| G2 | trung bình–cao (HVM-GraphRAG, MemGraphRAG, EvoTrustRAG chưa đọc) | cao (typing chạy CPU) | ngắn | cần chứng minh hơn hẳn prompt LLM có typing |
| G7 | trung bình (EvoTrustRAG có thể có WFR) | cao | ngắn nhất | an toàn, hợp PLOS ONE / Sci Rep; đồng thời là động lực cho G2 |
| G1 | cao | cao | ngắn | dễ bị coi là chủ đề cũ; có rủi ro rò rỉ đáp án |
| G2+G1 | trung bình | cao | trung bình | khớp tiêu đề "Relation-Aware"; ablation rõ ràng |
| G3+G8 | trung bình (thiếu benchmark, cần tìm thêm) | trung bình (cần subset Wikidata) | dài | có lợi thế ngôn ngữ; rủi ro LLM đã giải quyết được |

Gợi ý sơ bộ (để bạn phản hồi trước Phase B): **G7 → G2+G1** như một chuỗi, trong đó G7 cung cấp động lực và metric, còn G2+G1 là phương pháp.
G3+G8 có thể là một phần mở rộng (loại alias có thời gian hiệu lực) bên trong G2.

## 3. Việc cần làm để giảm rủi ro novelty (chuyển vào `07`)

1. Đọc full text HVM-GraphRAG (2607.24861), MemGraphRAG (2606.00610), EvoTrustRAG (2608.07933), ConflictRAG (2605.17301), EvidenceConflict,
   Ragability (LREC 2026), ConflictQA (2604.11209), "When Facts Change" (Findings ACL 2026), T-GRAG (2508.01680), TimeR4 (EMNLP 2024).
   Cần bạn mở `arxiv.org` trong network settings, hoặc attach PDF.
2. Đọc paper gốc CONFLICTS (Cattan et al. 2025): định nghĩa chính xác các loại và quy trình annotate.
3. Kiểm tần suất apparent conflict **mức passage** trong CONFLICTS (gán nhãn tay khoảng 50 query) để trả lời câu hỏi "có hiếm không" của G2.
