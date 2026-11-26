# 08 — Pre-pilot review (2026-11-05)

Vòng review này diễn ra trước pilot chú thích. Commit được review là `485aa3b` (cuối Phase C).
- Số dòng trong cột "Bằng chứng" là tại `485aa3b`; xem lại bằng `git show 485aa3b:<path>`.
- Repo vẫn là prototype; không có số liệu nào ở đây là kết quả.
- Mọi kiểm tra trong vòng này là mock/offline trong cloud: không tải weights, không gọi API trả phí.

## 1. Kiểm chứng các nhận xét của bạn

Đã đối chiếu từng nhận xét kỹ thuật với code. **Tất cả đều đúng**, nên không có nhận xét nào cần phản bác.

| # | Nhận xét | Bằng chứng tại `485aa3b` | Sửa trong vòng này | Test |
|---|---|---|---|---|
| 1 | Frame của G2⁺ mang `gold` | `src/kgrerank/perturb/operators.py:42` `QuestionFrame` có trường `gold` (`:47`); G2⁺ nhận đúng kiểu này (`src/kgrerank/conflict/signals.py:21`, `:51`) | `InferenceFrame` không có `gold` (`src/kgrerank/frames/schema.py`); `frame_from_construction` bỏ `gold` khi dùng fixture synthetic | `tests/test_g2plus.py::test_no_gold_in_inference_frames`, `tests/test_frames.py` |
| 2 | Extractor không nhận câu hỏi | `src/kgrerank/conflict/typer.py:135` gọi `self.extractor.extract(c.pid, c.text)`, không có câu hỏi | typer truyền `ex.question`; `extract_with_status(pid, text, question)` | `tests/test_llm_path.py::test_extractor_receives_the_question` (kiểm nội dung prompt) |
| 3 | Baseline/fallback hỏi về "other evidence" mà không đưa evidence đó | `src/kgrerank/rerankers/llm_judge.py:18`–`19` (`PROMPT_V0`); fallback của G2⁺ dùng cùng prompt (`conflict/typer.py:23`, `:184`) | hai prompt `single_passage_v1` và `inter_context_v1`, mỗi prompt khai báo information access (`ACCESS`, `NEVER_ACCESSED`) | `tests/test_llm_path.py::test_prompts_never_contain_the_reference_answer_and_show_declared_context` |
| 4 | `max_tokens=4`; output lỗi bị đọc thành `UNKNOWN` | `llm_judge.py:51` và `conflict/typer.py:185` (`max_tokens=4`); `parse_decision` (`llm_judge.py:24`–`29`) trả `Decision.UNKNOWN` cho mọi output không đọc được | output JSON, `max_tokens` 256; status `ok / parse_error / truncated / thinking_output / backend_error`; lỗi cho `decision = None`, không bao giờ thành `UNKNOWN` | `tests/test_llm_path.py::test_statuses_are_explicit`, `::test_failures_are_not_unknown_decisions` |
| 5 | Mention mơ hồ bị gán entity của câu hỏi | `conflict/signals.py:56`–`58` (`default_question_entity`) | bỏ luật này; mơ hồ → `UNKNOWN` ở linker, frame parser và typer | `tests/test_g2plus.py::test_ambiguous_subject_is_never_resolved_to_the_question_entity`, `tests/test_frames.py::test_ambiguous_and_unlinked_stay_unresolved` |
| 6 | Single-best-value bị biến thành conflict | `conflict/policy.py:119`–`125` (`R-single-best-value` trả `conflict`; SBV chỉ hạ confidence) | `R-sbv-not-exclusive` → unknown | `tests/test_g2plus.py::test_single_best_value_is_not_exclusive` |
| 7 | Hai phát biểu không ngày tháng được coi là cùng thời điểm | `conflict/signals.py:179` (`Basis("assumption", note="both_unscoped")` cho `OVERLAP`); `policy.py:110`–`112` chỉ chặn khi property là `MUTABLE` | `TemporalRelation.UNKNOWN`; `R-time-unknown` trừ khi property được chú thích `stable` | `tests/test_g2plus.py::test_missing_dates_need_a_stable_property` |
| 8 | Separator, exception, constraint deprecated | separator được ghi (`signals.py:202`) nhưng `policy.py` không dùng; constraint deprecated vẫn được nạp (`kg/view.py:184`–`193`, không lọc rank) | `R-separator-uncertain`, `R-exception` → unknown; bỏ constraint deprecated (`kg/view.py:193`) | `tests/test_g2plus.py::test_constraint_details_block_conflicts` |
| 9 | Định nghĩa WFR trong docs khác code | `docs/PLAN.md:241` và `metrics/conflict.py:59`–`67`: passage cần giữ = mọi COMPATIBLE; `docs/ANNOTATION_GUIDELINES.md:74`: WFR dựa vào `answer_support` | hai biến thể có tên: `wfr_compat_v1` và `wfr_support_v1`; khóa cũ `wfr` bị bỏ (không đổi nghĩa ngầm) | `tests/test_eval_accounting.py::test_wfr_variants` |
| 10 | `llm_calls` đếm thiếu | `pipeline.py:132` lấy `Ranking.llm_calls`; typer chỉ đếm fallback (`conflict/typer.py:186`), không đếm extraction; chưa có frame parse | ghi event cho từng call theo role (`frame_parse`, `extract`, `judge`/`typer`, `fallback`): token ước tính, token server báo, latency, status; cache policy `none` | `tests/test_llm_path.py::test_judge_usage_counts_every_call`, `tests/test_g2plus.py::test_fallback_statuses_and_usage` |
| 11 | Passage chưa judge bị coi là non-relevant | `pipeline.py:126`–`130`: Recall/nDCG/MRR tính trên toàn `r.order` với `gold = ex.gold_pids`, kể cả passage CONFLICTS chưa chú thích | full-list chỉ báo cáo khi judgment phủ toàn pool; luôn có bản condensed `*_cond` (`metrics/retrieval.py` `condense`) | `tests/test_eval_accounting.py::test_unjudged_passages_are_not_negatives` |
| 12 | 2Wiki: supporting fact của dataset bị trộn với nhãn người | `annotation/export.py:66`: `is_gold = c.is_gold and decision is not CONTRADICTING`, sửa cờ dataset mà không ghi lại | `meta.relevance_source`, `meta.relevance_judged_pids`, `meta.dataset_supporting_pids`; xung đột được liệt kê trong `<gold>.report.json` | `tests/test_annotation.py::test_export_keeps_dataset_supporting_facts_apart` |
| 13 | Thống kê bỏ qua sự phụ thuộc giữa passage cùng câu hỏi | `metrics/decision.py` `decision_metrics` không có CI; `metrics/stats.py` `bootstrap_ci` dành cho metric mức query | `typing_report`: cluster bootstrap theo câu hỏi, báo `n_questions`, failure rate | `tests/test_eval_accounting.py::test_typing_report_counts_failures_and_clusters_by_question` |

Tài liệu chính thức về constraint được đọc lại ngày 2026-11-05, 04:51 UTC (`?action=raw`, HTTP 200):
- `Help:Property_constraints_portal/Single_best_value`: "It may have any number of values, but exactly one of them
  (the "best" one, by whatever criteria) should have preferred rank."
- `Help:Property_constraints_portal/Single_value`:
  - "If sources list several possible P19 and P20, all values can be included and should not be removed."
  - P4155 (separator): "multiple statements with the same value do not constitute a violation of this constraint as
    long as they have different qualifiers for the properties specified here."
  - "It's possible that the item is a rare, but legitimate exception to the constraint, and nothing should be done."

Hệ quả cho policy v0.2: SBV không cho tính độc quyền; single-value chỉ là soft evidence; có separator hoặc exception
thì → unknown.

## 2. Thay đổi theo từng mục

1. **Question frame** (`src/kgrerank/frames/`):
   - LLM parse (`PROMPT_V1` chỉ nhận câu hỏi) + linking tự động. Entity hay property mơ hồ hoặc không tìm thấy thì giữ
     trạng thái `ambiguous` / `unlinked`.
   - Câu hỏi multi-hop, comparison hoặc không biểu diễn được → `unsupported` → fallback (`R-frame-unsupported`).
   - Thời gian tương đối chỉ giải theo snapshot của benchmark, không theo ngày chạy.
   - Mỗi frame ghi source, `parser_version`, model, trạng thái linking và lỗi.
   - Có `coverage` trên toàn tập, audit trên một mẫu tất định không nhìn nhãn (`scripts/frames/frame_audit.py`), và
     human-framed diagnostic với source riêng (`human_audit`).
   - Chạy mock trên 109 câu hỏi của main: 0 frame supported. Đây là smoke test on toy data – not a result: MockLLM
     không parse được gì.
2. **Sample và annotator:**
   - sample v1, seed, ID và manifest giữ nguyên (`manifests/annotation_sample_v1.json` không đổi);
   - `A2: TBD`; hướng dẫn ngắn cho A2: `docs/annotation/A2_quickstart.md`;
   - usability trial trên sheet A1 không được báo cáo như pilot hai annotator hay IAA;
   - LLM không điền trước nhãn;
   - Complementary: 44 passage của main đến từ 6 câu hỏi, chỉ là exploratory.
3. **Codebook v0.1 (draft)**, `docs/annotation/codebook_v0.1.md`; v0 giữ nguyên để lưu lịch sử:
   - chú thích tương đối với reference answer;
   - thiếu ngày tháng không có nghĩa là cùng thời điểm; ngày đăng không phải thời điểm fact có hiệu lực;
   - `CONTRADICTING` cần đủ ba điều kiện (cùng fact, cùng scope đã xác lập, loại trừ nhau);
   - `predicate_mismatch` có thể là bridge fact;
   - `answer_support` được định nghĩa rõ;
   - flag `reference_unclear` / `reference_suspect` được báo cáo có và không có item gắn flag.

   Ghi trong `docs/annotation/CHANGELOG.md`. v1 chỉ được freeze sau pilot thật.
4. **Policy v0.2** (`src/kgrerank/conflict/policy.py`): xem mục 6–8 của bảng §1. Policy được sửa **trước** khi có bất
   kỳ kết quả G2⁺ nào trên dữ liệu tự nhiên. S3 vẫn chỉ là upper-bound diagnostic.
5. **Đường LLM:** xem mục 2–5 và 10 của bảng §1. Information access của từng system được ghi vào output
   (`pipeline.information_access`).
6. **Metric:**
   - xem mục 9–13 của bảng §1;
   - thêm denominator `den:*` và số passage theo `label_source`. "Chưa chú thích" (`unlabelled`) khác "người chú
     thích UNKNOWN" (`manual`).
7. **Model** (`configs/msi/qwen3_8b.yaml`):
   - `Qwen/Qwen3-8B`, revision `b968826d9c46dd6066d109eabc6255188de91218`, BF16, non-thinking;
   - sha256 của 4 file nhỏ (không phải weights) đã kiểm;
   - lệnh vLLM và trường `chat_template_kwargs` là **[UNVERIFIED]**;
   - không có claim nào về throughput.
8. **Trình tự đánh giá** khóa ở `docs/ANNOTATION_GUIDELINES.md` §12 và `docs/PLAN.md` C.1.
9. **PR:** xem §6.

## 3. Lỗi tự phát hiện trong vòng này

- **Macro-F1 trong `metrics/decision.py`:**
  - Class vắng mặt trong cả gold lẫn prediction từng được tính F1 = 0, làm thấp macro-F1 của stratum nhỏ. Nay chỉ
    lấy trung bình trên các class có mặt (quy ước scikit-learn).
  - Bản nháp đầu của `typing_report` (chưa commit) bỏ call lỗi khỏi macro-F1. Nay call lỗi được tính là sai, và mọi
    tỷ lệ dùng chung mẫu số.
  - Test: `tests/test_eval_accounting.py::test_macro_f1_skips_classes_absent_from_gold_and_prediction`.
- **Sai sót của tôi khi viết config:** trong `configs/msi/qwen3_8b.yaml`, tôi đã gõ phần đuôi của các giá trị sha256
  **trước khi tính**; chỉ 20 ký tự đầu là thật. Sai sót đã được phát hiện trước khi commit. Các giá trị đã được thay
  bằng sha256 tính thật và kiểm lại cả 4 file (OK).

## 4. Kiểm tra offline (2026-11-05, cloud, chỉ mock)

| Kiểm tra | Kết quả |
|---|---|
| `make lint` (ruff check + format) | sạch; 101 file |
| `make test` | 104 passed, 0,70 s |
| `make smoke` | chạy xong khoảng 1,1 s; output có nhãn "smoke test on toy data – not a result" |
| `scripts/run_pilot.py --config configs/pilot_local.yaml` | 453 ví dụ, khoảng 10 s (plumbing, MockLLM) |
| `scripts/audit/check_citations.py reports/*.md` | 184/184 OK (trích dẫn code bên thứ ba) |
| Trích dẫn ở §1 | 25 trích dẫn và 2 kiểm "không có" đều khớp với `485aa3b` (script tạm, không commit) |
| Manifest mẫu | `manifests/annotation_sample_v1.json` không đổi |

## 5. Vấn đề còn mở

Xem `reports/07_uncertainties.md` §2, §4 và §6. Quan trọng nhất:
- **Snapshot CONFLICTS** `[2025-04-03, 2025-06-15]`:
  - cận dưới là ngày lớn nhất của kết quả search trong `conflicts.jsonl`;
  - cận trên là ngày của arXiv 2506.08500v2;
  - **bạn cần xác nhận**.
- **Snapshot 2Wiki:** không có, nên thời gian tương đối trong câu hỏi 2Wiki giữ `unresolved`.
- **Trường vLLM tắt thinking chưa kiểm:** `chat_template_kwargs: {enable_thinking: false}`. Trang Qwen docs trả 403.
  Bước đầu trên MSI phải kiểm bằng một request thật; harness đánh dấu mọi reply có `<think>` là lỗi.
- **KG view cho mention của câu hỏi:** slice hiện tại không phủ 109 câu hỏi, nên linking thật phải xây trên MSI.
- **Thiếu chú thích mutability:** policy v0.2 hiếm khi cho KG quyết `CONTRADICTING`.
  - Trên slice, chỉ 2/29 property có single-value (P1696, P585), còn 11/29 có single-best-value (gồm P19/P20).
    Không property nào có chú thích mutability.
  - Bước KG chủ yếu hòa giải apparent conflict; genuine conflict đi qua LLM fallback.
  - Đây là hệ quả thiết kế cần ghi trong paper.

## 6. PR #1

Quan sát trong phiên (2026-11-05), [Thuy-g/paper3-kg-conflict-rerank#1](https://github.com/Thuy-g/paper3-kg-conflict-rerank/pull/1):
- 0 review, 0 review thread, 0 comment;
- 0 check run; combined status `pending` với 0 status (repo chưa có CI).

Không có review nào để trả lời. PR giữ mở để bạn duyệt; không merge.
