# 04 — Xếp hạng hướng nghiên cứu (cuối Phase C, 2026-11-04)

Cập nhật từ `03_candidate_gaps.md` §2, dùng bằng chứng mới của Phase B/C. Đây là khuyến nghị, **không phải kết quả**.
G7 → G2⁺ vẫn là **working hypothesis**; novelty **chưa kiểm** bằng literature search có hệ thống (`07` §1).

## 1. Bằng chứng mới ảnh hưởng tới xếp hạng

1. **FCFR không xác định trên dữ liệu tự nhiên nếu chưa có chú thích mức passage.**
   - Cả 2Wiki, CONFLICTS và Ragability đều không có nhãn apparent-conflict (`03b` §5.1).
   - Đã thiết kế và pre-register tập 400 item độc lập với KG (`docs/ANNOTATION_GUIDELINES.md`). Đây là điều kiện
     cần cho cả G7 lẫn G2⁺.
2. **Cardinality constraint của Wikidata là signal yếu** (`02d` §2.1).
   - Chỉ 2/29 property có single-value; 11/29 là single-best-value.
   - P19/P20 chỉ có status suggestion; có property mang tới 25 exception.
   - → G2⁺ nên là "qualifier/identity-first, constraint chỉ là prior mềm".
3. **G2⁺ skeleton trên dữ liệu toy** (*smoke test on toy data – not a result*; circular vì perturbation sinh từ cùng
   KG):
   - S3 tự quyết 12/13 passage có nhãn, sai 0;
   - S2 tự quyết 8/13, sai 0, chuyển LLM 5;
   - S0/S1 chuyển LLM toàn bộ;
   - số LLM call giảm dần 27 → 19 → 15 khi tăng quyền truy cập KG.

   Điều này chỉ cho thấy **cơ chế cascade chạy đúng**, không cho thấy hiệu quả.
4. **Consensus (S0–S2) có điểm yếu cấu trúc.** Khi pool chỉ có claim sai cho đúng mốc thời gian, consensus không thể
   biết. Skeleton trả UNKNOWN thay vì đoán, nhưng điều này giới hạn lợi ích của KG khi bị mask.

## 2. Xếp hạng

| Hạng | Hướng | Novelty risk | Khả thi trên 1× RTX 5090 | Thời gian tới kết quả đầu tiên (ước đoán) | Khả năng công bố (OA journal) |
|---|---|---|---|---|---|
| **1** | **G7** — chẩn đoán false conflict filtering trên tập chú thích độc lập (FCFR theo reason + WFR, natural vs synthetic) | trung bình (WFR mức query của EvoTrustRAG đã có; FCFR mức passage theo reason chưa thấy trong 18 paper đã audit — **[UNVERIFIED]** ngoài phạm vi đó) | cao: baseline LLM-filter 7–8B qua vLLM | ngắn: chú thích ≈ 19 giờ công + vài giờ GPU (`06`) | cao nếu protocol chú thích và agreement chặt chẽ (PLOS ONE / Sci Rep) |
| **2** | **G2⁺** — KG-first, qualifier/identity-aware typing với LLM fallback (G2 + G3 lõi) | trung bình–cao: phải vượt LLM-only typer (prompt MemGraphRAG) **ở setting S2**, không chỉ S3 | cao (typing chạy CPU; LLM cho extraction/fallback) | trung bình: cần question frame cho dữ liệu tự nhiên (`07` §2) | cao nếu thắng ở S2 với CI rõ; nếu chỉ thắng ở S3 thì claim phải thu hẹp |
| 3 | G2+G1 (consistency + typing) | trung bình | cao | trung bình | dùng làm ablation trong bài G2⁺, không tách bài |
| 4 | G3+G8 (temporal, cross-lingual alias) | G3 đã vào lõi G2⁺; G8 trung bình, chưa kiểm | trung bình | dài | để bài sau (lợi thế ngôn ngữ vi/ja) |
| 5 | G1 đơn lẻ | cao | cao | ngắn | không khuyến nghị (chủ đề cũ, rủi ro rò rỉ đáp án) |

## 3. Điều kiện go/no-go (pre-register **sau** pilot, **trước** khi chạy G2⁺ trên tập chú thích)

Chưa chốt con số. Ngưỡng sẽ được suy ra từ variance và MDE của pilot (`docs/PLAN.md` B.6). Các mệnh đề cần
falsify:

- **G7 (vấn đề có thật không?)** Trên tập chú thích, FCFR_paired@5 của các LLM filter mạnh có lớn hơn đáng kể so với
  baseline relevance-only không?
  - Nếu CI cho thấy FCFR không khác 0, hoặc nhỏ hơn MDE, thì động lực cho G2⁺ yếu → báo cáo kết quả âm, dừng G2⁺.
- **G2⁺ (KG có giúp không?)** Ở **S2** (không phải S3), G2⁺ có giảm FCFR so với LLM-only typer mà GER không giảm quá
  một non-inferiority margin (chốt sau pilot) không?
  - Nếu chỉ thắng ở S3 → claim chỉ còn "upper bound khi có KG-oracle".
- **Cascade (tiết kiệm LLM call)** Báo cáo coverage của bước KG (tỷ lệ không cần LLM) và accuracy trên phần đó, tách
  theo nguồn dữ liệu.

## 4. Đề xuất bước tiếp theo

1. **Bạn làm (không cần GPU):**
   - pilot annotation 40 item → codebook v1;
   - main annotation (A1 400 item, A2 120 item).
2. **Trên MSI** (`05`): chạy baseline relevance-only, LLM-filter, LLM-typer (MemGraphRAG prompt) trên **pool đầy
   đủ** của 109 câu hỏi → đo FCFR/GER/WFR, variance theo seed và MDE → pre-register ngưỡng.
3. Chỉ sau đó mới chạy G2⁺ (S0–S3) trên tập chú thích. Literature search có hệ thống trước khi viết (`07` §1).
