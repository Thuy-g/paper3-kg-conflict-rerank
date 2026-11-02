# 00 — Môi trường cloud session (Phase 0)

> Kiểm tra lúc `2026-11-02T12:40Z` (UTC). Đây là môi trường **cloud sandbox** dùng cho audit +
> prototype CPU, **không phải** phần cứng thí nghiệm thật (RTX 5090 / WSL2 — xem `CLAUDE.md` §2).

## 1. Phần cứng và hệ điều hành

Lệnh đã chạy: `nproc; free -h; df -h; nvidia-smi || true` (+ `lscpu`, `/etc/os-release`).

| Hạng mục | Kết quả |
|---|---|
| CPU | `nproc` = **4**; `Intel(R) Xeon(R) Processor @ 2.10GHz`, 1 thread/core, 1 socket |
| RAM | `free -h`: total **15Gi**, available 15Gi, swap 0B |
| Disk | `df -h /`: size 252G, used 8.9G, **avail 30G** (theo system note, `df` có thể không phản ánh đúng quota per-session) |
| GPU | `nvidia-smi: command not found` → **không có GPU** |
| OS | Ubuntu 24.04.5 LTS (noble), kernel `6.18.44-fc-v185`, x86_64 |
| Python | `python3` mặc định = **3.13.18** (`/usr/local/bin/python3`) — KHÔNG dùng; **Python 3.11.18** ở `/usr/bin/python3.11` (có `venv`, pip 24.0) |
| Tooling | `uv 0.11.32`, `ruff 0.16.9`, GNU Make 4.3, git 2.43.0, git-lfs |
| Secrets | Không có biến môi trường API key nào (chỉ kiểm tên biến, không in giá trị) |

Hệ quả: mọi thứ trong session này phải chạy được trên **CPU 4 nhân, ~15 GiB RAM**; không chạy
được vLLM/LLM thật → `MockLLM` là mặc định (đúng quy tắc 4).

## 2. Network policy (probe bằng HEAD/GET, không tải dữ liệu)

| Host / URL | Kết quả | Ý nghĩa |
|---|---|---|
| `https://pypi.org/simple/rank-bm25/` | 200 | cài package Python được |
| `https://huggingface.co/api/datasets/hotpotqa/hotpot_qa` | 200 | đọc metadata dataset trên HF được |
| `https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2/resolve/main/config.json` | 307 (redirect) | host model HF truy cập được (chưa tải thử file nào) |
| `https://datasets-server.huggingface.co/` | 404 ở root | host truy cập được; endpoint `/rows` chưa thử (Phase B) |
| `https://raw.githubusercontent.com/` | 301 | host truy cập được; quyền theo repo chưa thử |
| `https://github.com/STAIR-BUPT/TruthfulRAG` | **403**, body: `"GitHub access to this repository is not enabled for this session. Use add_repo to request access. ..."` | repo upstream **nằm ngoài scope** GitHub của session |
| `https://arxiv.org/abs/2511.10375` | **CONNECT 403** (curl); WebFetch: `getaddrinfo ENOTFOUND arxiv.org` | arXiv **bị chặn** bởi network policy |
| `https://www.wikidata.org/` | **CONNECT 403** | Wikidata **bị chặn** |

Proxy status (`$HTTPS_PROXY/__agentproxy/status` → `recentRelayFailures`) ghi:
`connect_rejected — gateway answered 403 to CONNECT (policy denial or upstream failure)` cho
`arxiv.org:443` và `www.wikidata.org:443`.

Hệ quả cho kế hoạch:
- **Không đọc được paper trên arXiv** trong session này → các claim về nội dung paper (section,
  công thức trong paper, venue) chỉ được kiểm qua README/code trong repo; phần còn lại ghi
  **[UNVERIFIED]**. Muốn mở: thêm `arxiv.org` vào *Allowed domains* trong Network access của
  cloud environment (xem https://code.claude.com/docs/en/cloud-environments#network-access).
- **Không truy vấn được Wikidata** → `TinyKG` (Phase C) là fixture viết tay, ghi rõ synthetic.
- **Upstream GitHub bị 403** → Phase A sẽ thử `git clone --depth 1` đúng như yêu cầu, ghi
  nguyên văn lỗi, rồi dùng các **fork đã attach** (`Thuy-g/*`) làm nguồn read-only.

## 3. Các fork đã được attach vào session (đã clone sẵn trong `/home/user/`)

| Thư mục | Remote | Branch checkout | HEAD commit | Ngày commit | Shallow? | Dung lượng |
|---|---|---|---|---|---|---|
| `ArbGraph` | `Thuy-g/ArbGraph` | `claude/wizardly-cannon-lofwfv` | `d98950fbf6b5ea45008d98e9dc582054ffe81c05` | 2026-09-03 | no | 520K |
| `GraphRAG-Benchmark` | `Thuy-g/GraphRAG-Benchmark` | `claude/wizardly-cannon-lofwfv` | `fdbab5959b18c96532580877ffe27d112bccc0ec` | 2026-06-07 | **yes** | 171M |
| `MAGIC` | `Thuy-g/MAGIC` | `claude/wizardly-cannon-lofwfv` | `f3df32cb85ff84dbfc17cd8870f82f13aa9647d3` | 2026-09-04 | no | 3.3M |
| `Relink` | `Thuy-g/Relink` | `claude/wizardly-cannon-lofwfv` | `135526bb0694d7eb4120c8d4d48bfe3ffd694124` | 2026-03-20 | no | 84M |
| `TruthfulRAG` | `Thuy-g/TruthfulRAG` | `claude/wizardly-cannon-lofwfv` | `231c9175f51a71a2407e38b8213f8ac910d46a6d` | 2025-12-18 | no | 22M |
| `kapipe` | `Thuy-g/kapipe` | `claude/wizardly-cannon-lofwfv` | `89aaeb94653698a13159bfc3168091c8527eb895` | 2026-10-27 | **yes** | 22M |
| `rag_conflicts` | `Thuy-g/rag_conflicts` | `claude/wizardly-cannon-lofwfv` | `81ba921dd684a93db41a7e9dda6b6a7c67348a88` | 2025-06-11 | no | 78M |

Ghi chú:
- Việc HEAD của fork trùng với HEAD của upstream là **[UNVERIFIED]** (upstream không truy cập được).
- `rag_conflicts/conflicts.jsonl` = 46.7 MB, 458 dòng (~100 KB/dòng) → khi làm tiny slice
  (Phase B) phải giới hạn theo **dung lượng** chứ không chỉ theo số ví dụ (quy tắc ≤ 50 MB tổng).
- Các fork này sẽ **không bị sửa, commit hay push** (quy tắc 2).
