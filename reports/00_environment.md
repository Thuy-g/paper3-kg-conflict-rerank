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
| `https://github.com/STAIR-BUPT/TruthfulRAG` (HTTP GET trang web) | **403**, body: `"GitHub access to this repository is not enabled for this session. Use add_repo to request access. ..."` | trang web/API GitHub của repo ngoài scope bị chặn. **Đính chính ở Phase A:** `git clone --depth 1` 7 repo upstream public đều **thành công** (exit 0) — xem `02_codebase_map.md` §1 |
| `https://arxiv.org/abs/2511.10375` | **CONNECT 403** (curl); WebFetch: `getaddrinfo ENOTFOUND arxiv.org` | arXiv **bị chặn** bởi network policy |
| `https://www.wikidata.org/` | **CONNECT 403** | Wikidata **bị chặn** |

Proxy status (`$HTTPS_PROXY/__agentproxy/status` → `recentRelayFailures`) ghi:
`connect_rejected — gateway answered 403 to CONNECT (policy denial or upstream failure)` cho
`arxiv.org:443` và `www.wikidata.org:443`.

**Cập nhật 2026-11-02 (sau khi owner thêm `arxiv.org` vào Allowed domains):** `curl https://arxiv.org/abs/…` và `/pdf/…` → **200**;
`export.arxiv.org` vẫn CONNECT 403; tool WebFetch vẫn báo `getaddrinfo ENOTFOUND arxiv.org`; `aclanthology.org` → CONNECT 403
(chi tiết ở `02b_extension_audit.md` §1). Như vậy: **đọc arXiv bằng `curl` từ sandbox**; paper trên ACL Anthology cần owner attach PDF.

Hệ quả cho kế hoạch (bản gốc Phase 0):
- **Không đọc được paper trên arXiv** trong session này → các claim về nội dung paper (section,
  công thức trong paper, venue) chỉ được kiểm qua README/code trong repo; phần còn lại ghi
  **[UNVERIFIED]**. Muốn mở: thêm `arxiv.org` vào *Allowed domains* trong Network access của
  cloud environment (xem https://code.claude.com/docs/en/cloud-environments#network-access).
- ~~Không truy vấn được Wikidata~~ → **Cập nhật 2026-11-04:** WDQS và Special:EntityData đã truy cập được (xem §4); Action API bị 429.
- ~~Upstream GitHub bị 403~~ → **Đính chính (Phase A):** chỉ trang web bị 403; `git clone --depth 1` các repo upstream
  public chạy được, nên không cần fallback sang fork. Fork chỉ còn dùng để đối chiếu hash.

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
- ~~Việc HEAD của fork trùng với HEAD của upstream là [UNVERIFIED]~~ → **đã kiểm ở Phase A: trùng cả 7 repo**
  (`02_codebase_map.md` §1).
- `rag_conflicts/conflicts.jsonl` = 46.7 MB, 458 dòng (~100 KB/dòng) → khi làm tiny slice
  (Phase B) phải giới hạn theo **dung lượng** chứ không chỉ theo số ví dụ (quy tắc ≤ 50 MB tổng).
- Các fork này sẽ **không bị sửa, commit hay push** (quy tắc 2).

## 4. Kiểm tra network lần 3 (2026-11-04, sau khi owner mở rộng allowlist)

Allowlist owner khai báo: `huggingface.co`, `*.huggingface.co`, `arxiv.org`, `export.arxiv.org`, `aclanthology.org`, `wikidata.org`,
`www.wikidata.org`, `query.wikidata.org`, và (đã/sẽ thêm) `dbpedia.org`, `www.dbpedia.org`, `downloads.dbpedia.org`, `mappings.dbpedia.org`.
Chỉ dùng request nhỏ: `HEAD`, range request 1 KB, hoặc query `ASK`. User-Agent: `kgrerank-prototype/0.1 (research prototype; low-volume; python/curl)`.

| Thời điểm (UTC) | Endpoint | Request | Kết quả | Kết luận |
|---|---|---|---|---|
| 03:33:27 | `aclanthology.org` | GET `/2026.findings-acl.103/` | 200, 43.622 B | ✅ trang ACL Anthology |
| 03:33:28 | `aclanthology.org` | HEAD `/2026.findings-acl.103.pdf`; GET range `0-1023` | 200 `application/pdf`; 206, 1.024 B | ✅ PDF trên ACL Anthology |
| 03:33:28 | `www.wikidata.org` | HEAD `/` | 301 → `/wiki/Wikidata:Main_Page` | ✅ |
| 03:33:28 | `wikidata.org` | HEAD `/` | 301 → `https://www.wikidata.org/` | ✅ |
| 03:33:29 → 03:34:30 | `www.wikidata.org/w/api.php` (Action API, `wbgetentities`) | GET `action=wbgetentities&ids=Q42&props=labels&languages=en&format=json` (+ 2 biến thể, cách nhau 3 s) | **HTTP 429**: "You are making too many requests to the API. Please follow the best practices at https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits." Có 1 lần trả 200 nhưng `labels` **rỗng** (dữ liệu không đáng tin) | ❌ **rate-limited** (IP egress dùng chung, `x-client-ip` của proxy) → **không dùng Action API** |
| 03:33:29 | `www.wikidata.org` | HEAD `/wiki/Special:EntityData/Q42.json` | 200 `application/json` | ✅ |
| 03:34:40 | `www.wikidata.org` | GET `/wiki/Special:EntityData/P580.json` | 200, 72.605 B | ✅ (JSON đầy đủ của property) |
| 03:33:29 | `query.wikidata.org` | GET `/sparql?format=json&query=ASK { wd:Q42 wdt:P31 wd:Q5 }` | 200 `application/sparql-results+json`, 38 B | ✅ WDQS |
| 03:33:29 | `huggingface.co` | GET `/api/datasets/ofai/RagabilityCorpus` | 200 | ✅ |
| 03:33:30 | `datasets-server.huggingface.co` | GET `/is-valid?dataset=ofai/RagabilityCorpus` | 200 | ✅ |
| 03:33:30 | `arxiv.org`, `export.arxiv.org` | HEAD `/abs/2606.00610` | 200, 200 | ✅ (export.arxiv.org nay đã mở) |
| 03:33:31 | `dbpedia.org` | HEAD `/` | 301 → `https://www.dbpedia.org/` | ✅ |
| 03:33:31 | `www.dbpedia.org` | HEAD `/` | 200 | ✅ |
| 03:33:47; thử lại 1 lần lúc 03:34:13 | `downloads.dbpedia.org` | HEAD `/` | `curl: (35) Recv failure: Connection reset by peer`; proxy ghi `ws_closed_mid_exchange — tunnel closed (code 1006) after 15s; 517 B sent, 39 B received` | ❌ **không truy cập được** → **dừng mọi phần phụ thuộc host này** (không tải file release DBpedia) |
| 03:33:48 | `mappings.dbpedia.org` | HEAD `/` | 301 → `/index.php/Main_Page` | ✅ |
| 03:33:48 | `databus.dbpedia.org` | HEAD `/` | 200 | ✅ (không có trong danh sách owner khai báo nhưng vẫn truy cập được) |
| 03:46:43 → 03:53:17 | `dbpedia.org/sparql` | 9 query nhỏ (`ASK`, `COUNT`, `SELECT … LIMIT ≤ 60`), xem `appendix/C_dbpedia_queries.tsv` | 200 | ✅ endpoint **live** (có thể khác release 2022.12.01) |
| 03:35:56 → 03:37:07 | `www.wikidata.org/wiki/<Help page>?action=raw` | 17 GET tuần tự, cách nhau 1–3 s, xem `appendix/B_wikidata_docs_fetch.tsv` | 15 × 200; 2 × **429** (`…/Qualifiers` thử lại thành công; `Help:Ranking` không thử lại) | ✅ có rate limit, cần nghỉ giữa các request |
| 03:50 | `github.com` (git) | `git clone --depth 1 --filter=blob:none --sparse` `Alab-NII/2wikimultihop`; sparse checkout chỉ `LICENSE`, `README.md` | exit 0; `.git` 224 KB | ✅ |
| ~03:55 | `pypi.org` | GET `/simple/pyyaml/` | 200 | ✅ cài package cho Phase B |

Hệ quả:
- **ACL Anthology và arXiv**: đọc được trực tiếp; không cần owner attach PDF nữa.
- **Wikidata**: dùng **WDQS** (chọn và lấy statement có điều kiện) và **Special:EntityData** (JSON đầy đủ cho một số ít entity/property).
  **Không dùng Action API** khi còn bị 429. Mọi request đều tuần tự, có nghỉ giữa các lần, và User-Agent mô tả rõ. Khi chạy trên máy MSI,
  nên đặt User-Agent có thông tin liên hệ của owner theo khuyến nghị của Wikimedia.
- **DBpedia**: phần audit dựa vào tài liệu trên `www.dbpedia.org`, `databus.dbpedia.org`, `mappings.dbpedia.org` và code extraction framework
  (GitHub). **Không tải** file `infobox-properties`, vì `downloads.dbpedia.org` không truy cập được (và theo quy tắc cũng không tải file lớn).
