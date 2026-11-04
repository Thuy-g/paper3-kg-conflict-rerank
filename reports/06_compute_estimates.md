# 06 — Ước tính chi phí (công thức + giả định, không phải đo đạc)

Mọi con số là ước tính. Giả định ghi rõ để bạn thay bằng số đo thật sau pilot.

## 1. Công chú thích (người)

**Giả định.** t = 1,5 phút/item cho A1/A2 và 2 phút/item ở pilot. Passage CONFLICTS dài trung bình 1.324 ký tự; 2Wiki
419 ký tự.

| Bước | Công thức | Ước tính |
|---|---|---|
| Pilot (2 người) | 40 × 2 phút × 2 người | ≈ 2,7 giờ |
| Main A1 | 400 × 1,5 phút | ≈ 10 giờ |
| Main A2 | 120 × 1,5 phút | ≈ 3 giờ |
| Adjudication | (30–50% của 120) × 3 phút | ≈ 1,8–3 giờ |
| **Tổng** | | **≈ 18–19 giờ công** |

## 2. LLM call cho pilot trên MSI

**Kích thước:** 109 câu hỏi, P = 998 passage trên pool đầy đủ.

**Số call cho mỗi system và seed:**
- LLM filter: tối đa min(top_m, pool) call mỗi câu, tức ≤ P call.
- G2⁺ với LLM extractor: P call cho extraction, cộng tối đa P call fallback ⇒ ≤ 2P.
- G2⁺ S3 dùng ít fallback hơn: trên toy data giảm 27 → 15 call; tỷ lệ thật **[UNVERIFIED]**.

**Kịch bản xấu nhất:** 5 seed decoding (như EvoTrustRAG [paper p.5]).

| Thành phần | Số call |
|---|---|
| LLM filter | 5 × P = 4.990 |
| LLM-only typer | 5 × P = 4.990 |
| G2⁺ S0–S3 | 4 × 5 × 2P = 39.920 |
| **Tổng** | **≈ 50.000 call** |

**Token mỗi call (ước tính).**
- Prompt khoảng 150 token cộng passage (khoảng 1.324/4 ≈ 330 token với CONFLICTS).
- Output ≤ 128 token.
- Tổng ≈ 0,6k token mỗi call, tức ≈ **30 triệu token** cho kịch bản xấu nhất.

**Thời gian.** Với vLLM, model 7–8B và batching, throughput **[UNVERIFIED]** khoảng vài nghìn token/s, nên tổng
khoảng **vài giờ GPU**. Đo throughput thật ở bước pilot trước khi chạy hết.

## 3. CPU trong cloud (đã đo, không phải ước tính)

- `make test`: 78 test, khoảng 0,5 s.
- `make smoke`: dưới 1 s.
- Sampling: khoảng 1,2 s.
- Plumbing run trên 453 ví dụ: 4 s.

## 4. Chi phí tiền

- 0 nếu chỉ dùng vLLM local và `MockLLM`.
- API trả phí bị chặn mặc định (budget guard). Nếu dùng phải đặt `ALLOW_PAID_API=1`, `MAX_API_CALLS`,
  `MAX_API_TOKENS` và ước tính lại theo bảng giá lúc đó.
