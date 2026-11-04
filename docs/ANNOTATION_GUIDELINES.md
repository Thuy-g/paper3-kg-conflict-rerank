# Protocol chú thích độc lập mức passage (independent natural-evidence evaluation set)

Phiên bản protocol: 1.0 (2026-11-04). Codebook cho annotator (tiếng Anh, vì annotator thứ hai có thể không đọc
tiếng Việt): `docs/annotation/codebook_v0.md`. Lịch sử thay đổi: `docs/annotation/CHANGELOG.md`.

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
- **Lý do có `answer_support`.**
  - Recall/nDCG trên CONFLICTS cần biết passage nào là "gold".
  - WFR cần biết passage nào nên được giữ.
  - Trường này tách "có mâu thuẫn không" khỏi "có hữu ích cho câu trả lời không".
- **Định nghĩa IRRELEVANT dùng chung** cho annotation và label protocol: passage **không liên quan tới fact được
  hỏi**. Hệ quả: passage `predicate_mismatch` (ví dụ nơi mất thay cho nơi sinh) là IRRELEVANT. Label protocol của
  perturbation được nâng lên v1 cho khớp (`docs/PLAN.md` B.3).

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

1. **Codebook v0** (`docs/annotation/codebook_v0.md`) — đã có.
2. **Pilot.**
   - A1 và A2 cùng chú thích độc lập 40 item pilot bằng `sheets/pilot_A1.csv` và `sheets/pilot_A2.csv`; mỗi người
     có một thứ tự khác nhau, nhóm theo câu hỏi.
   - Nộp bằng `submit.py --codebook v0`.
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

- **Complementary** chỉ có 6 query trong main (7 query có reference). Kết luận riêng cho stratum này rất yếu.
- **Misinformation** chỉ có 4 query trong main: CONTRADICTING tự nhiên sẽ hiếm. GER trên tập này có thể thiếu power;
  synthetic chỉ bổ sung ở mức stress-test.
- **Truncation:** 44/400 passage chạm giới hạn 2.000 ký tự (cố ý, để khớp với text method thấy). Annotator gắn cờ
  `passage_truncated`.
- **Thời điểm của reference CONFLICTS:** chỉ biết là "up-to-date" lúc tạo dataset [paper p.5]; ngày cụ thể
  **[UNVERIFIED]**. Annotator suy ra từ ngữ cảnh (codebook §2).
- **Clustering:** item tập trung theo câu hỏi, nên mọi CI phải bootstrap theo câu hỏi, không theo item.
