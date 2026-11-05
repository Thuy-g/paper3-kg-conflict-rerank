# 07 — Tổng hợp [UNVERIFIED], vấn đề mở và việc cần kiểm (cập nhật 2026-11-05)

Gom từ các nguồn sau:
- `02_codebase_map.md` §5;
- `02b_extension_audit.md` §7;
- `02c_extension_audit_2.md` §8;
- `02d_kg_sources_and_constraints.md` §6;
- `03_candidate_gaps.md` §3;
- `03b_phaseB_harness.md` §6;
- Phase C và vòng pre-pilot review (`08_prepilot_review.md`).

Mục đã giải quyết bị gạch và ghi nơi giải quyết.

## 1. Novelty và literature (ảnh hưởng claim của paper)

| # | Mục | Kiểm ở đâu, bằng cách nào |
|---|---|---|
| N1 | Chưa có lượt tìm có hệ thống cho ba chủ đề: "passage-level false conflict filtering theo reason", "KG-first conflict typing + reranking", "mutability + inter-context conflict" | arXiv qua `curl` (cloud đã truy cập được), ACL Anthology (đã truy cập được); ghi query và ngày tìm |
| N2 | EvidenceConflict (9/2026) chưa đọc | xin bạn attach PDF hoặc link |
| N3 | Tiêu chí và APC của IEEE Access / PLOS ONE / Scientific Reports mới chỉ thấy qua snippet tìm kiếm | đọc trang chính thức của journal trước khi chọn nơi nộp |
| N4 | Trích dẫn cho condensed-list metric (Sakai, SIGIR 2007) trong docstring của `metrics/retrieval.py` là **[UNVERIFIED]** | kiểm bản paper trước khi trích trong bài |

## 2. Thiết kế đánh giá

| # | Mục | Việc cần làm |
|---|---|---|
| D1 | ~~Question frame cho dữ liệu tự nhiên~~ → **đã quyết (2026-11-05):** LLM parse + linking tự động; audit bằng người trên mẫu riêng; human-framed diagnostic báo cáo riêng | chạy trên MSI (`05` §4) |
| D2 | Codebook v0.1 là draft; mọi edge case E1–E8 là đề xuất | pilot 40 item → v1 (`docs/ANNOTATION_GUIDELINES.md` §5) |
| D3 | ~~Mở rộng Complementary~~ → **không mở rộng, không có sample v2** (2026-11-05) | báo cáo: 44 passage Complementary của main đến từ 6 câu hỏi, chỉ là exploratory |
| D4 | Snapshot của CONFLICTS: cửa sổ `[2025-04-03, 2025-06-15]` (cận dưới từ ngày lớn nhất trong `conflicts.jsonl`, cận trên từ ngày arXiv 2506.08500v2; chưa kiểm ngày của v1) | **bạn xác nhận** trước khi chạy frame cho main |
| D5 | A1 = bạn (dự kiến); **A2: TBD**. Rủi ro thiên lệch vì A1 cũng là người thiết kế method | chú thích trước khi chạy G2⁺; so sánh phân phối nhãn của A1 với A2 |
| D6 | Hằng số confidence của `policy_v0.2` và λ được đặt a priori, chưa có cơ sở | giữ cố định; thay đổi nào cũng tạo version mới, có giải thích, chọn trên engineering pilot (tập pilot), không trên main |
| D7 | Consensus (S0–S2) có thể sai khi claim sai chiếm đa số | báo cáo riêng stratum Misinformation; so với S3 (upper bound) |
| D8 | Ngưỡng 10 điểm % / 2 điểm % / 50% không phải tiêu chí khoa học cố định | suy ra từ variance/MDE của engineering pilot; pre-register trước bước 5 (`04` §3) |
| D9 | Chất lượng của LLM extractor trên dữ liệu tự nhiên chưa đo | kiểm tay một mẫu trong engineering pilot |
| D10 | KG view phủ mention của 121 câu hỏi chưa có; slice hiện tại chỉ có 200 ID | xây trên MSI theo đề xuất ở `05` §3 (chưa cài) |
| D11 | Chưa có chú thích mutability (`stable`/`mutable`) cho property nào; trên slice chỉ 2/29 property có single-value (P1696, P585: không phải property thường được hỏi), 11/29 có single-best-value (gồm P19/P20) | hệ quả: policy v0.2 hiếm khi để KG quyết `CONTRADICTING`. Bước KG chủ yếu hòa giải apparent conflict; genuine conflict đi qua LLM fallback. Ghi rõ trong paper; chú thích mutability (nếu làm) phải có nguồn và version |
| D12 | Baseline LLM-only typer theo prompt `conflict_detection` của MemGraphRAG làm việc trên triple và không bao giờ trả IRRELEVANT | viết adapter có version; kiểm prompt, input, information access và attribution MIT trước khi dùng |
| D13 | Frame audit lấy câu hỏi của main | sửa parser sau khi xem audit main tạo `parser_version` mới; kết quả của nó là exploratory |
| D14 | 2Wiki không có snapshot | thời gian tương đối giữ `unresolved`; báo cáo số câu hỏi bị ảnh hưởng |

## 3. Dữ liệu, licence

| # | Mục | Việc cần làm |
|---|---|---|
| L1 | Licence **data** của 2WikiMultiHopQA (repo Apache-2.0; README không nêu licence data) | hỏi tác giả hoặc tìm trong paper/website trước khi công bố dữ liệu dẫn xuất |
| L2 | Licence data của ContextConflict (repo và HF card không khai báo) | email tác giả nếu muốn dùng |
| L3 | Licence data của corpus GraphRAG-Bench; HotpotQA/MuSiQue/ConcurrentQA trong Relink | kiểm trước khi dùng |
| L4 | Phần code kế thừa HippoRAG trong MemGraphRAG | kiểm licence nếu tái dùng code (prompt dùng với attribution MIT) |
| L5 | Ánh xạ "DBpedia infobox-properties ~2023-03-08" sang version Databus; nội dung file release (host tải bị chặn trong cloud) | kiểm trên máy local nếu chạy nhánh DBpedia |
| L6 | ~~Dùng dữ liệu WikiRecentChanges~~ → **không dùng** theo quyết định của bạn (2026-11-04); có test kiểm | — |

## 4. Phần cứng và phần mềm (máy MSI)

| # | Mục | Kiểm bằng |
|---|---|---|
| H1 | PyTorch và vLLM có hỗ trợ RTX 5090 không (Blackwell, cần compute capability (12, 0)); model card Qwen3-8B cần `vllm>=0.8.5` | `05` §2; ghi version thật bằng `scripts/msi/record_env.py` |
| H2 | Throughput, VRAM và thời gian chạy của Qwen3-8B BF16 | đo ở engineering pilot; chưa có claim nào |
| H3 | Kích thước model cross-encoder trước khi tải (quy tắc ≤ 100 MB ở cloud) | HF API, kiểm trước khi tải |
| H4 | vLLM có nhận `seed`, `presence_penalty` từ `ChatOpenAI` (MemGraphRAG/TruthfulRAG) không; LiteLLM `api_base` cho Ragability | thử trên máy thật |
| H5 | Extra `ce` (`sentence-transformers==6.2.0`) chưa cài, chưa test | cài và chạy test trên máy local |
| H6 | Trường request `chat_template_kwargs: {enable_thinking: false}` của vLLM là **[UNVERIFIED]** (qwen.readthedocs.io trả HTTP 403 qua proxy) | một request thật (`HANDOFF.md` §4 bước 5); reply có `<think>` là lỗi |
| H7 | `record_env.py` cần PyYAML trong venv của vLLM | nếu thiếu: `pip install pyyaml` trong venv đó, hoặc chạy script bằng venv của project (khi đó không ghi được version vLLM) |

## 5. Mục đã giải quyết

- ~~Mã cụ thể của các constraint Wikidata~~: đã kiểm bằng WDQS và tài liệu chính thức (`02d` §1, §2.1).
  - Trang Single value và Single best value được đọc lại ngày 2026-11-05 (`08` §1).
- ~~Wikidata có truy cập được không~~: WDQS và `Special:EntityData` truy cập được; Action API trả 429 (`00` §4).
- ~~Cách pin dữ liệu Wikidata~~: `?revision=<lastrevid>` cho response giống từng byte (`02d` §2.1).
- ~~Licence và revision Ragability~~: CC-BY-SA-4.0, revision `2251634e…`, 53 dòng (`manifests/ragability_fetch.json`).
- ~~Tần suất apparent conflict mức passage trong CONFLICTS~~: thay bằng tập chú thích pre-register (400 item).
- ~~Chọn model LLM~~: `Qwen/Qwen3-8B`, revision pin, BF16, non-thinking (`05` §1).
- ~~WFR trong docs khác code~~: hai biến thể có tên, `wfr_compat_v1` và `wfr_support_v1` (`08` §1).
- ~~Single-best-value bị coi là độc quyền; hai phát biểu không ngày tháng bị coi là cùng thời điểm~~: `policy_v0.2`
  (`08` §1).

## 6. Kiểm chứng vòng pre-pilot review

Bảng đối chiếu từng nhận xét với code (path, symbol, số dòng tại `485aa3b`) nằm ở `08_prepilot_review.md` §1. Mọi
nhận xét đều đúng.
