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

## 2. LLM call trên MSI (cập nhật 2026-11-05; ước tính theo công thức, không phải đo đạc)

**Kích thước main:** Q = 109 câu hỏi, P = 998 passage trên pool đầy đủ. Engineering pilot trên tập pilot (12 câu
hỏi) nhỏ hơn khoảng 9 lần.

**Số call cho mỗi seed:**
- Frame parse: Q call, chạy một lần (seed 0).
- Mỗi LLM baseline (`single_passage_v1`, `inter_context_v1`): tối đa min(top_m, pool) call mỗi câu, tức ≤ P.
- G2⁺ với LLM extractor, cho mỗi KG setting: P call extraction cộng tối đa P call fallback, tức ≤ 2P. Không có cache
  (`cache_policy: none`), nên mỗi setting gọi lại extraction.

**Kịch bản xấu nhất:** 5 seed (như EvoTrustRAG [paper p.5]) và 4 setting S0–S3.

| Thành phần | Số call |
|---|---|
| Frame parse | Q = 109 |
| Hai LLM baseline | 2 × 5 × P = 9.980 |
| G2⁺ S0–S3 | 4 × 5 × 2P = 39.920 |
| LLM-only typer (MemGraphRAG, nếu có adapter) | 5 × P = 4.990 |
| **Tổng** | **≈ 55.000 call** |

**Token mỗi call (cận trên).**
- Prompt khoảng 150 token, cộng passage khoảng 1.324/4 ≈ 330 token (CONFLICTS).
- Prompt `inter_context_v1` có thêm tối đa 5 passage × 600 ký tự ≈ 750 token.
- Output bị chặn ở `max_tokens = 256`. Output JSON thật thường ngắn hơn, nhưng chưa đo.
- Cộng theo từng thành phần, tổng cận trên khoảng **60 triệu token**.

**Thời gian và throughput:** không ước tính. Theo yêu cầu của bạn, không có claim nào về throughput hay tổng thời gian
chạy. Cả hai được đo ở engineering pilot (`latency_s` và token theo từng call được ghi trong output), rồi mới lập kế
hoạch cho main.

## 3. CPU trong cloud (đã đo, không phải ước tính)

Đo ngày 2026-11-05, trừ khi ghi khác:
- `make test`: 104 test, khoảng 0,7 s.
- `make smoke`: khoảng 1,1 s.
- Sampling: khoảng 1,2 s (đo ngày 2026-11-04).
- Plumbing run `configs/pilot_local.yaml` trên 453 ví dụ: khoảng 10 s. Ngày 2026-11-04 là 4 s; thời gian tăng vì
  có thêm cluster bootstrap và metric condensed.

## 4. Chi phí tiền

- 0 nếu chỉ dùng vLLM local và `MockLLM`.
- API trả phí bị chặn mặc định (budget guard). Nếu dùng phải đặt `ALLOW_PAID_API=1`, `MAX_API_CALLS`,
  `MAX_API_TOKENS` và ước tính lại theo bảng giá lúc đó.
