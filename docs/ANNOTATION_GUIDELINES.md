# Protocol chú thích độc lập mức passage (independent natural-evidence evaluation set)

Phiên bản protocol: 1.1 (2026-11-05, sau pre-pilot review).
- Codebook cho annotator (tiếng Anh, vì annotator thứ hai có thể không đọc tiếng Việt): **`docs/annotation/codebook_v0.1.md`**
  (bản nháp cho pilot). Bản `codebook_v0.md` được giữ nguyên làm lịch sử.
- Hướng dẫn ngắn cho A2: `docs/annotation/A2_quickstart.md`. Lịch sử thay đổi: `docs/annotation/CHANGELOG.md`.
- **Annotator:** A1 = bạn (dự kiến). **A2: TBD**, chưa giả định đã có người.

## 1. Mục đích và nguyên tắc

- **Bằng chứng chính.** Tập này là **independent natural-evidence evaluation set**: bằng chứng chính cho claim G7
  (và về sau G2⁺).
- **Synthetic chỉ để stress-test.** Perturbation synthetic sinh từ Wikidata chỉ là **capability/stress-test set**,
  không phải bằng chứng chính (`reports/02d_kg_sources_and_constraints.md` §5.4).
- **Độc lập với KG và method.** Nhãn được tạo **không** dùng KG, **không** dùng method, **không** dùng LLM. LLM
  không bao giờ là gold annotator, cũng không được pre-fill nhãn.
- **Giả thuyết, chưa phải kết luận.** G7 → G2⁺ vẫn chỉ là working hypothesis.
- **Không chốt ngưỡng trước.** Không chốt ngưỡng 10 điểm % / 2 điểm % / 50% trước khi có pilot thật.
- **Đơn vị chú thích:** cặp `(question, candidate passage)`.

## 2. Population, sampling và pre-registration

Cấu hình: `configs/annotation_v1.yaml`. Script: `scripts/annotation/sample_items.py`. Seed: `20261104`.

**Pre-registration.**
- Manifest `manifests/annotation_sample_v1.json` ghi:
  - seed;
  - sha256 của các file nguồn;
  - toàn bộ item ID được chọn, kèm stratum và sha256 của text từng passage.
- Manifest được commit ở `d197d5d` **trước khi có bất kỳ code hay prediction nào của G2⁺**.
- Sampling chỉ dùng trường của dataset: category, loại câu hỏi, vị trí passage, cờ supporting fact của 2Wiki
  (chỉ để cân bằng). Không dùng output của model, ranking hay score.

**Sampling frame.**

- CONFLICTS (`conflicts.jsonl` của fork, 458 query):
  - chỉ giữ query **có reference answer** của dataset;
  - text passage tạo bằng **cùng converter** với harness (`short_text`, tối đa 2.000 ký tự), nên annotator
    gán nhãn đúng phần text mà method nhìn thấy;
  - passage rỗng hoặc trùng lặp trong cùng query bị loại.
- 2WikiMultiHopQA: 500 ví dụ `samples.json` của fork Relink.

**Phát hiện từ dữ liệu.**
- CONFLICTS chỉ viết reference answer cho No conflict, Outdated và Misinformation [paper CONFLICTS p.5].
- Vì vậy Complementary chỉ có **7/115** query dùng được.

| Stratum CONFLICTS | Query đủ điều kiện |
|---|---|
| outdated | 62 |
| no_conflict | 161 |
| complementary | 7 |
| misinformation | 5 |

**Kết quả sampling.** Pilot và main **không chung câu hỏi**.

| Tập | CONFLICTS | 2Wiki | Tổng | Câu hỏi |
|---|---|---|---|---|
| Pilot | outdated 12, no_conflict 9, complementary 4, misinformation 5 | 10 | **40** | 12 |
| Main | outdated 146, no_conflict 75, complementary 44 (6 query, lấy hết, tối đa 8/query), misinformation 35 (4 query, lấy hết, tối đa 9/query) | 100 (25 câu × 2 supporting + 2 khác, phân tầng theo loại câu hỏi) | **400** | 109 |
| Double (con của main) | phân tầng theo stratum, chọn ngẫu nhiên ở mức item | | **120** (30%) | 71 |

Muốn mở rộng Complementary cần thêm một bước **viết reference answer** cho các query chưa có, do người thứ ba (không
phải A1/A2) làm, **trước** khi chú thích, và phải pre-register. Đây là quyết định của bạn; mặc định chưa làm.

## 3. Nhãn

- **Gold semantic decision:** `COMPATIBLE | CONTRADICTING | IRRELEVANT | UNKNOWN`. Định nghĩa và quy trình từng
  bước: codebook §3–§4.
- **Trường phụ:**
  - `reasons`: multi-label, 11 loại của schema v1;
  - `answer_support`: `yes | partial | no | unclear`;
  - `confidence`, `rationale`, `reason_note`, `flags`.
- `reasons` **không bao giờ** tự quyết định decision: codebook §5 cho ví dụ cùng một reason đi với các decision
  khác nhau.
- **Đây là reference-relative annotation.**
  - Annotator đánh giá passage **so với reference answer của dataset**, không xác minh độc lập mọi fact ngoài đời.
  - Reference answer chỉ hiển thị cho annotator. **Không bao giờ** được đưa vào input của method hay baseline
    (frame parser, extractor, typer, fallback). Test `tests/test_llm_path.py` kiểm điều này.
- **Cờ `reference_unclear` / `reference_suspect`.** Item có cờ được giữ lại và đếm. Mọi metric chính được báo cáo
  hai lần: trên toàn bộ tập và khi loại các item có cờ (sensitivity analysis). Không âm thầm bỏ item nào.
- **Lý do có `answer_support`** (tách compatibility khỏi usefulness):
  - CONFLICTS: `is_gold` = `answer_support = yes`. Chỉ passage đã chú thích có relevance judgment, nên chỉ báo cáo
    retrieval metric dạng **condensed** (bỏ passage chưa chú thích), không báo cáo như qrels đầy đủ.
  - WFR có hai biến thể đặt tên rõ: `wfr_compat_v1` (giữ mọi COMPATIBLE) và `wfr_support_v1` (giữ COMPATIBLE có
    `answer_support` yes/partial).
- **Định nghĩa IRRELEVANT dùng chung** cho annotation và label protocol: passage **không liên quan tới fact được
  hỏi, kể cả bridge fact cần thiết**.
  - Với câu hỏi một bước, passage `predicate_mismatch` (nơi mất thay cho nơi sinh) là IRRELEVANT.
  - Với câu hỏi nhiều bước, predicate khác có thể là bridge fact → COMPATIBLE (codebook v0.1 §3, §5).
  - Label protocol của perturbation (v1) chỉ sinh câu hỏi một bước, nên quy tắc IRRELEVANT ở đó vẫn đúng.
- **Chưa chú thích ≠ người chú thích là UNKNOWN.** Passage chưa chú thích có `label_source = unlabelled`; passage
  được người gán UNKNOWN có `label_source = manual`. Báo cáo đếm riêng hai loại.

## 4. Blinding

**Annotator chỉ thấy:**
- item ID dạng opaque, không lộ stratum hay vị trí;
- question và reference answer;
- title, date (nếu có) và text của passage.

**Annotator không thấy:**
- category của CONFLICTS (stratum);
- cờ supporting fact của 2Wiki;
- prediction của G2⁺ hay của baseline;
- quyết định Wikidata/KG của method;
- reranking score;
- nhãn của annotator kia.

Annotator được dặn không mở `data/annotation/v1/key.jsonl`, `manifests/` hay dataset gốc. Blinding dựa vào cam kết
này; cần ghi rõ trong báo cáo.

**Không dùng:** web search, KG, LLM.

**Thiếu evidence thì gán UNKNOWN**, không suy đoán (codebook §1).

## 5. Quy trình

1. **Codebook v0.1** (`docs/annotation/codebook_v0.1.md`) — bản nháp cho pilot.
2. **Pilot.**
   - A1 và A2 cùng chú thích độc lập 40 item pilot bằng `sheets/pilot_A1.csv` và `sheets/pilot_A2.csv`; mỗi người
     có một thứ tự khác nhau, nhóm theo câu hỏi.
   - Nộp bằng `submit.py --codebook v0.1`.
   - **Khi chưa có A2:** A1 có thể thử usability của codebook trên vài item của sheet A1. Lần thử đó **không** được
     báo cáo là pilot hai annotator hay inter-annotator agreement, và không thay cho pilot thật.
3. **Phân tích bất đồng ở pilot.**
   - Chạy `agreement.py --set pilot`.
   - Đọc từng item bất đồng, sửa wording và edge case của codebook.
   - Số liệu pilot **không** dùng làm kết quả IAA cuối cùng.
4. **Freeze codebook v1.**
   - Tạo `docs/annotation/codebook_v1.md`.
   - Ghi vào `CHANGELOG.md`: thay đổi, lý do, item pilot nào dẫn tới thay đổi.
   - Commit, rồi ghi commit hash vào CHANGELOG **trước** main annotation.
5. **Main annotation.**
   - A1 chú thích **400** item (`sheets/main_A1.csv`). A2 chú thích **120** item double (`sheets/main_A2.csv`).
   - A1 **không biết** item nào được chú thích kép.
   - Hai người làm độc lập.
6. **Nộp và đóng băng.** Mỗi người chạy:

   ```bash
   .venv/bin/python scripts/annotation/submit.py --sample-dir data/annotation/v1 --set main --annotator A1 --codebook v1 --file <sheet đã điền>
   ```

   - Script kiểm tra bộ nhãn (giá trị hợp lệ, đủ item, ràng buộc như CONTRADICTING ⇒ `answer_support = no`).
   - Sau đó ghi bản chuẩn hóa và sha256. Nộp lại bị từ chối.
7. **Đo agreement:**

   ```bash
   .venv/bin/python scripts/annotation/agreement.py --sample-dir data/annotation/v1 --set main
   ```

8. **Adjudication.**
   - `adjudicate.py prepare` tạo sheet cho mọi item bất đồng về decision, reasons hoặc `answer_support`.
   - Người adjudicate điền nhãn cuối, phương pháp (`discussion | third_annotator | owner_decision`), người
     quyết và ghi chú.
   - `adjudicate.py merge` tạo `main_gold.jsonl`, giữ **cả nhãn trước adjudication của A1 và A2** lẫn nhãn
     cuối, kèm manifest sha256 của mọi input.
9. **Xuất cho harness:**

   ```bash
   .venv/bin/python scripts/annotation/export_gold.py --config configs/annotation_v1.yaml --set main
   ```

   - Tạo pool đầy đủ theo schema v1. Passage không được chú thích để `UNKNOWN`.
   - `is_gold`: CONFLICTS dùng `answer_support = yes`; 2Wiki dùng supporting fact của dataset, trừ khi chú thích
     là CONTRADICTING.
   - Script kiểm sha256 của text với manifest.

## 6. Báo cáo agreement (trên tập double)

- **Decision:**
  - raw agreement;
  - Cohen's kappa, CI 95% bằng **cluster bootstrap theo câu hỏi** (nhiều item chung một câu hỏi);
  - confusion matrix;
  - phân phối nhãn của từng người;
  - breakdown theo stratum.
- **Reasons (multi-label):**
  - Krippendorff's alpha với **MASI distance** (Passonneau 2006);
  - mean Jaccard; exact-set agreement;
  - kappa nhị phân cho từng reason, kèm tần suất (kappa không ổn định khi reason hiếm).
- **`answer_support`:** raw agreement, kappa.
- **Không đặt ngưỡng agreement** làm tiêu chí thành công trước pilot (yêu cầu của bạn). Diễn giải agreement sau
  pilot, dựa trên phân tích bất đồng.

## 7. Adjudication

- Chỉ bắt đầu sau khi **cả hai** đã nộp (submission đã bị đóng băng).
- Item đồng ý trên cả decision, reasons và `answer_support` được tự động chốt (method `agreement`). Item còn lại
  phải có nhãn cuối, method, người quyết và ghi chú.
- Item chỉ có A1 giữ nhãn A1 (method `single_annotator`). Báo cáo tách riêng kết quả trên tập double (đã
  adjudicate) và trên toàn bộ tập.
- **Rủi ro:** nếu A1 là người thiết kế method, có thể có thiên lệch hệ thống.
  - So sánh phân phối nhãn A1 với A2 trên tập double.
  - Chú thích **xong trước** khi chạy G2⁺ trên tập này.

## 8. Quản lý phiên bản

- Sau khi freeze v1, **mọi** thay đổi nhãn hoặc định nghĩa đều phải:
  - tạo version mới (`codebook_v1.1`, …);
  - ghi lý do vào CHANGELOG;
  - liệt kê item bị ảnh hưởng và cách xử lý (chú thích lại hay giữ nguyên).
- Không sửa submission đã đóng băng; muốn chú thích lại thì nộp file mới với version mới.
- Thay đổi sampling (ví dụ thêm Complementary) phải là **sample mới** (`v2`), có manifest riêng, không sửa v1.

## 9. Dữ liệu và licence

- Text nằm trong `data/annotation/v1/` (gitignored); chỉ commit ID, hash và nhãn.
  - CONFLICTS: text là trang web bên thứ ba, chỉ dùng local.
  - 2Wiki: licence data **[UNVERIFIED]**.
- Nếu công bố tập nhãn: chỉ công bố **ID + nhãn + hash**, kèm script tái tạo từ nguồn gốc.

## 10. Giới hạn đã biết

- **Complementary:** 44 passage trong main chỉ thuộc **6 câu hỏi** (7 query có reference). Số passage không phải
  số quan sát độc lập. Mọi kết quả riêng cho stratum nhỏ này (và Misinformation) chỉ mang tính **thăm dò**.
- **Misinformation** chỉ có 4 query trong main: CONTRADICTING tự nhiên sẽ hiếm. GER trên tập này có thể thiếu power;
  synthetic chỉ bổ sung ở mức stress-test.
- **Truncation:** 44/400 passage chạm giới hạn 2.000 ký tự (cố ý, để khớp với text method thấy). Annotator gắn cờ
  `passage_truncated`.
- **Thời điểm của reference CONFLICTS:** chỉ biết là "up-to-date" lúc tạo dataset [paper p.5]; ngày cụ thể
  **[UNVERIFIED]**. Annotator suy ra từ ngữ cảnh (codebook §2).
- **Clustering:** item tập trung theo câu hỏi, nên mọi CI phải bootstrap theo câu hỏi, không theo item.

## 11. Question frame (input của method, không phải nhãn)

- G2⁺ cần frame cho mỗi câu hỏi: subject QID, property, mốc thời gian, loại câu hỏi.
- **Phương án chính (quyết định 2026-11-05): LLM parse câu hỏi + linking tự động.** Script:
  `scripts/frames/parse_frames.py`.
- Parser chỉ nhận **text câu hỏi** và mô tả snapshot. Nó không nhận reference answer, nhãn passage, cờ supporting
  fact hay reasons.
- **Không đoán.** Entity mơ hồ hoặc không tìm thấy giữ trạng thái `ambiguous` / `unlinked`. Câu hỏi nhiều bước,
  so sánh hay ngoài khả năng biểu diễn được đánh dấu unsupported. Khi đó G2⁺ chỉ dùng fallback.
- **Thời gian tương đối** ("current", "this year") chỉ được giải theo snapshot của benchmark đã cấu hình
  (`configs/frames_v1.yaml`), không bao giờ theo ngày chạy thí nghiệm.
- **Coverage** được báo cáo trên **toàn bộ** câu hỏi, kể cả câu KG không xử lý được.
- **Audit bằng người:**
  - một mẫu câu hỏi deterministic riêng (`frame_audit.py sample`, seed riêng), độc lập với nhãn passage;
  - người audit chỉ thấy câu hỏi;
  - kết quả so sánh với parser ở `frame_audit.py compare`.
- **Frame do người sửa** chỉ được dùng cho một lần chạy **human-framed diagnostic**, báo cáo riêng, không trộn với
  pipeline tự động.
- **Prompt của parser** (`frame_parser_v1`) chỉ được sửa trong engineering pilot trên câu hỏi pilot. Nếu sửa sau khi
  đã xem audit hay kết quả trên main, đó là một `parser_version` mới và kết quả của nó là exploratory.

## 12. Trình tự đánh giá (khóa)

1. Sửa protocol và integration (vòng này).
2. Pilot annotation 40 item với A1/A2.
3. Sửa và freeze codebook v1.
4. Engineering pilot trên MSI: chỉ để kiểm plumbing, prompt format, tỷ lệ lỗi và thời gian; **không** dùng main
   set. Dữ liệu là tập pilot (12 câu hỏi, 40 item, không trùng câu hỏi nào với 109 câu của main):
   `configs/msi/frames_pilot_qwen3.yaml`, rồi `configs/msi/engineering_pilot.yaml`. Template cho bước 5:
   `configs/msi/main_eval.example.yaml`.
5. Main annotation, rồi evaluation theo kế hoạch đã khóa.

Main set **không** được dùng để chọn prompt, policy, λ hay sửa threshold theo kết quả mong muốn. Nếu cần điều chỉnh
thiết kế sau khi đã xem kết quả main, phần đó được ghi là **exploratory** và cần một đánh giá độc lập tiếp theo.
