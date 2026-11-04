# 07 — Tổng hợp [UNVERIFIED], vấn đề mở và việc cần kiểm (cuối Phase C, 2026-11-04)

Gom từ:
- `02_codebase_map.md` §5;
- `02b_extension_audit.md` §7;
- `02c_extension_audit_2.md` §8;
- `02d_kg_sources_and_constraints.md` §6;
- `03_candidate_gaps.md` §3;
- `03b_phaseB_harness.md` §6;
- các phát hiện của Phase C.

Mục đã giải quyết bị gạch và ghi nơi giải quyết.

## 1. Novelty và literature (ảnh hưởng claim của paper)

| # | Mục | Kiểm ở đâu, bằng cách nào |
|---|---|---|
| N1 | Chưa có lượt tìm có hệ thống cho "passage-level false conflict filtering theo reason", "KG-first conflict typing + reranking", "mutability + inter-context conflict" | arXiv qua `curl` (cloud đã truy cập được), ACL Anthology (đã truy cập được); ghi query và ngày tìm |
| N2 | EvidenceConflict (9/2026) chưa đọc | xin bạn attach PDF hoặc link |
| N3 | Tiêu chí và APC của IEEE Access / PLOS ONE / Scientific Reports mới thấy qua snippet tìm kiếm | đọc trang chính thức của journal trước khi chọn nơi nộp |

## 2. Thiết kế đánh giá (Phase C)

| # | Mục | Việc cần làm |
|---|---|---|
| D1 | **Question frame** (subject QID, property, mốc thời gian) cho dữ liệu tự nhiên chưa có; G2⁺ cần nó | quyết phương án (a) LLM parse + linking hay (b) gán tay độc lập (`05` §4) |
| D2 | Codebook v0 chưa qua pilot; mọi edge case E1–E8 là đề xuất | pilot 40 item → v1 (`docs/ANNOTATION_GUIDELINES.md` §5) |
| D3 | Complementary chỉ có 7 query có reference answer (6 trong main) | quyết có thêm bước viết reference độc lập (sample v2) hay không |
| D4 | Thời điểm cụ thể của reference answer CONFLICTS ("up-to-date" lúc tạo dataset [paper p.5]) | ghi giả định trong codebook; xem metadata dataset nếu có |
| D5 | Rủi ro thiên lệch nếu A1 cũng là người thiết kế method | chú thích trước khi chạy G2⁺; so sánh phân phối nhãn A1 với A2 |
| D6 | Hằng số confidence của policy v0 và λ của reranker được đặt a priori, chưa có cơ sở | giữ cố định khi đánh giá; mọi thay đổi phải tạo version policy mới, chọn trên dữ liệu khác tập chú thích |
| D7 | Consensus (S0–S2) có thể sai khi claim sai chiếm đa số | báo cáo riêng theo stratum Misinformation; so với S3 |
| D8 | Ngưỡng go/no-go (10 điểm % / 2 điểm % / 50%) chưa chốt | suy ra từ variance/MDE của pilot, pre-register trước khi chạy G2⁺ (`04` §3) |
| D9 | `PatternExtractor` chỉ dùng cho template synthetic | dữ liệu tự nhiên cần LLM extractor; đo chất lượng extraction trên một mẫu kiểm tay |

## 3. Dữ liệu, licence

| # | Mục | Việc cần làm |
|---|---|---|
| L1 | Licence **data** 2WikiMultiHopQA (repo Apache-2.0; README không nêu licence data) | hỏi tác giả hoặc tìm trong paper/website trước khi công bố dữ liệu dẫn xuất |
| L2 | Licence data ContextConflict (repo và HF card không khai báo) | email tác giả nếu muốn dùng |
| L3 | Licence data corpus GraphRAG-Bench; HotpotQA/MuSiQue/ConcurrentQA trong Relink | kiểm trước khi dùng |
| L4 | Phần code kế thừa HippoRAG trong MemGraphRAG | kiểm licence nếu tái dùng code (prompt dùng với attribution MIT) |
| L5 | Ánh xạ "DBpedia infobox-properties ~2023-03-08" sang version Databus; nội dung file release (host tải bị chặn trong cloud) | kiểm trên máy local nếu chạy nhánh DBpedia |
| L6 | ~~Dùng dữ liệu WikiRecentChanges~~ → **không dùng** theo quyết định của bạn (2026-11-04); có test kiểm | — |

## 4. Phần cứng và phần mềm (máy MSI)

| # | Mục | Kiểm bằng |
|---|---|---|
| H1 | PyTorch, vLLM hỗ trợ RTX 5090 (Blackwell, cần compute capability (12, 0)) | `05` §1; ghi version thật |
| H2 | Throughput vLLM cho model 7–8B | đo ở pilot (`06` §2) |
| H3 | Kích thước model cross-encoder trước khi tải (quy tắc ≤ 100 MB ở cloud) | HF API, kiểm trước khi tải |
| H4 | vLLM có nhận `seed`, `presence_penalty` từ `ChatOpenAI` (MemGraphRAG/TruthfulRAG) không; LiteLLM `api_base` cho Ragability | thử trên máy thật |
| H5 | Phiên bản extra `ce` (`sentence-transformers==6.2.0`) chưa cài, chưa test | cài và chạy test trên máy local |

## 5. Mục đã giải quyết trong Phase B/C

- ~~Mã cụ thể của các constraint Wikidata~~: đã kiểm bằng WDQS và tài liệu chính thức (`02d` §1, §2.1).
- ~~Wikidata có truy cập được không~~: WDQS và `Special:EntityData` truy cập được; Action API trả 429 (`00` §4).
- ~~Cách pin dữ liệu Wikidata~~: `?revision=<lastrevid>` cho response giống từng byte (`02d` §2.1).
- ~~Licence và revision Ragability~~: CC-BY-SA-4.0, revision `2251634e…`, 53 dòng (`manifests/ragability_fetch.json`).
- ~~Tần suất apparent conflict mức passage trong CONFLICTS~~ → được thay bằng tập chú thích pre-register (400 item).
