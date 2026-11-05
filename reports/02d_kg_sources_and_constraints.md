# 02d — Nguồn KG, Wikidata property constraints và DBpedia `infobox-properties`

Kiểm chứng trước Phase B, ngày 2026-11-04 (cloud session). Mọi truy cập mạng là request nhỏ, tuần tự, có
`sleep` giữa các request, User-Agent `kgrerank-prototype/0.1 (research prototype; low-volume; python/curl)`
(không chứa email). Kết quả network: `reports/00_environment.md` §4. Bản raw (wikitext, JSON) chỉ nằm trong
scratchpad của session, **không commit**; URL, thời điểm và sha256 đầy đủ nằm ở
`reports/appendix/B_wikidata_docs_fetch.tsv` và `reports/appendix/C_dbpedia_queries.tsv` để kiểm lại.

## 0. Tóm tắt

1. **Constraint là guidance, không phải axiom.** Tài liệu chính thức của Wikidata viết: "Constraints are hints, not
   firm restrictions, and are meant as a help or guidance to the editor. They can have exceptions". Vì vậy G2⁺ chỉ
   dùng constraint như **soft evidence có provenance**. Không có rule "single-value + hai object khác nhau ⇒ genuine
   contradiction".
   Dữ liệu thật (§2.1) củng cố điều này:
   - chỉ 2/29 property trong slice khai báo single-value;
   - P19/P20 là single-best-value với status *suggestion*;
   - có property tới 25 exception.
2. **DBpedia `infobox-properties` là generic (raw) extraction, không phải mapping-based.** Nó **không** có:
   - entity type, class hierarchy;
   - domain/range cho `dbp:` property;
   - cardinality constraint;
   - temporal qualifier tương đương P580/P582/P585;
   - rank hay statement-level qualifier.

   Alias chỉ xuất hiện dạng literal không định kiểu (`dbp:otherName "Saigon"`). → Phương án **B không đủ** cho G2⁺.
3. **Không thể nói "related work đều dùng Wikidata".** Trong 18 paper đã audit:
   - 2 paper dùng Wikidata **trực tiếp** làm source KG để sinh benchmark (MAGIC, When Facts Change);
   - 4 paper dùng **dataset được xây từ Wikidata** (Relink và MemGraphRAG qua 2WikiMultiHopQA; TimeR4 qua
     TimeQuestions; ContextConflict qua ConflictBank);
   - 11 paper không dùng KG có cấu trúc nào: chúng dùng Wikipedia/web/search/tài liệu dài, và nhiều paper tự
     xây graph từ text;
   - 1 survey không tính.
4. **Khuyến nghị sau khi cố falsify: A cho core, cộng một nhánh DBpedia có điều kiện, đăng ký trước ("C-staged").**
   - Core (Phase B–C và claim chính của paper) dùng Wikidata.
   - Nhánh DBpedia chỉ chạy nếu core thành công, và phải dùng generic + mappings + ontology (`instance-types`,
     `redirects`, ontology), không chỉ `infobox-properties`.
   - Default của bạn **đứng vững** sau falsification, với 3 sửa đổi (§5.3).
5. **Vấn đề làm thay đổi cách đánh giá (không phải blocker): circularity và answer leakage.**
   - 2WikiMultiHopQA, ConflictBank, TimeQuestions và MAGIC đều xây từ Wikidata.
   - Nếu nhãn synthetic sinh từ Wikidata và method cũng tra Wikidata, kết quả gần như tautological.
   - Cần các setting KG tách bạch, protocol masking, và một tập có nhãn độc lập với KG (§5.4).

## 1. Wikidata property constraints — tài liệu chính thức

### 1.1 Trang đã tải (`https://www.wikidata.org/wiki/<Trang>?action=raw`)

| Trang | UTC | HTTP | Trích nguyên văn / nội dung |
|---|---|---|---|
| `Help:Property_constraints_portal` | 03:35:56 | 200 | "Constraints are hints, not firm restrictions, and are meant as a help or guidance to the editor. They can have exceptions: for example, the town of Q668224 had the cat Q7627362 as honorary mayor." · P2303: "Lists known exceptions to the constraint. On the items listed under this parameter, the constraint is not checked." |
| `…/Single_value` (Q19474404) | 03:36:12 | 200 | "many identifiers (P213, P646, …) would generally only have a single value, as well as many non-identifier properties like P19 and P20." · "If sources list several possible P19 and P20, all values can be included and should not be removed. The most trustworthy value can be tagged with preferred rank" · "Statements that are backed up by sources that are believed to be incorrect should be tagged with deprecated rank." · "It's possible that the item is a rare, but legitimate exception to the constraint, and nothing should be done." · P4155 (separator): "multiple statements with the same value do not constitute a violation of this constraint as long as they have different qualifiers for the properties specified here." |
| `…/Single_best_value` (Q52060874) | 03:36:14 | 200 | "It may have any number of values, but exactly one of them (the "best" one, by whatever criteria) should have preferred rank." Ví dụ `wd:Q64 wdt:P6` ("current mayor of Berlin"): `wdt:` chỉ trả về giá trị "best". |
| `…/Multi_value` (Q21510857) | 03:36:16 | 200 | "This constraint type is rarely used, but some properties that usually have many values are P161, P3103 and P3161." |
| `…/Inverse` (Q21510855) | 03:36:21 | 200 | inverse property khai báo bằng qualifier P2306 (ví dụ P25 ↔ P40) |
| `…/Symmetric` (Q21510862) | 03:36:27 | 200 | ví dụ P3373, P26, P47, P190 |
| `…/Contemporary` (Q25796498) | 03:36:28 | 200 | start time = min của P569/P571/P580/P585, end time = max của P570/P576/P582/P585; "Values with deprecated rank are ignored"; nhóm "relative location" gồm P131, P17, … |
| `…/Subject_class` (Q21503250) | 03:36:51 | 200 | subject type ("domain"); đường P279 (subclass of) được tính |
| `…/Value_class` (Q21510865) | 03:36:54 | 200 | value type ("range") |
| `…/Required_qualifiers` (Q21510856) | 03:36:57 | 200 | ví dụ P35 nên có P580 |
| `…/Qualifiers` (Q21510851) | 03:36:23 **429** → retry 03:37:01 | 200 | allowed qualifiers (ví dụ P3300 cho phép P580, P582, P1932) |
| `Help:Qualifiers` | 03:37:04 | 200 | qualifier có thể "constrain the validity of the value" và cho biết "at what point of time the values are/were accurate" |
| `Help:Ranking` | 03:37:07 | **429** | không dùng; ngữ nghĩa rank lấy từ hai trang Single value và Single best value |

`…/Type`, `…/Value_type` và `…/Mandatory_qualifiers` chỉ là trang redirect ngắn (58–65 bytes).

### 1.2 Kiểm tra ID bằng WDQS (2026-11-04T03:37:35Z)

- Endpoint: `https://query.wikidata.org/sparql`. Response sha256 `5cb8cd660d78f200…` (đầy đủ trong appendix B).
- Truy vấn: `SELECT ?e ?label ?desc WHERE { VALUES ?e { … 49 ID … } OPTIONAL { ?e rdfs:label ?label
  FILTER(lang(?label)="en") } OPTIONAL { ?e schema:description ?desc FILTER(lang(?desc)="en") } }`.
- Cả 49 ID đều resolve. Description khớp với tài liệu, ví dụ:
  - Q19474404 "…generally contains a single value";
  - Q52060874 "…generally contains a single "best" value";
  - Q21510857 "…generally contains more than one value";
  - Q21502408 "mandatory constraint" / Q62026391 "suggestion constraint";
  - P580 "time an entity begins to exist or a statement starts being valid";
  - P582 "…a statement stops being entirely valid or no longer be true";
  - P585 "…existed or a statement was true".

Chữ **"generally"** nằm ngay trong định nghĩa của cả ba loại cardinality constraint.

### 1.3 Hệ quả cho thiết kế (ràng buộc cứng cho Phase B/C)

- **R1.** Constraint chỉ là soft evidence. Mỗi constraint được ghi kèm:
  - loại (Q-ID);
  - status (P2316: mandatory hay suggestion);
  - separators (P4155);
  - danh sách exception (P2303);
  - cờ "subject nằm trong danh sách exception".
- **R2.** Hai giá trị khác nhau cho một property single-value **không** tự suy ra contradiction. Tài liệu nêu ít nhất 5
  khả năng hợp lệ:
  1. legitimate exception;
  2. hai statement được phân biệt bằng separator qualifier;
  3. một giá trị deprecated;
  4. nhiều nguồn mâu thuẫn, cùng được giữ, một giá trị preferred;
  5. passage nói về thời điểm hoặc entity khác.
- **R3.** Rank `deprecated` nghĩa là được *nguồn tin cậy cho là sai*, không phải "sai trong thế giới". Nó là evidence,
  không phải ground truth.
- **R4.** `wdt:` (truthy) chỉ trả giá trị best-rank. Slice phải dùng `p:`/`ps:`/`pq:` (full statements) để thấy giá
  trị non-best, rank và qualifier.
- **R5.** Hierarchy/granularity **phụ thuộc thời gian**.
  - Trang Contemporary liệt kê P131, P17 trong nhóm "relative location".
  - Nhưng ở dữ liệu thật (§2.1), property P131 (rev 2555801353) **không** mang constraint
    Q25796498.
  - Tính phụ thuộc thời gian nằm ở **qualifier của từng statement**: ví dụ 6/6 statement P131
    của Saint Petersburg có P580/P582.
  - Vì vậy signal phải đọc từ statement, không suy ra từ constraint.

## 2. Sáu signal tách rời (input của G2⁺; Phase B chỉ định nghĩa schema, không kết hợp)

| Signal | Mức | Giá trị | Nguồn | Không được suy ra từ |
|---|---|---|---|---|
| `cardinality_constraint` | property | `single_value`, `single_best_value`, `multi_value`, `none_declared`, `unknown` + status, separators, exceptions, `subject_is_exception` | P2302 trên property | — |
| `mutability_class` | property (+ instance) | `stable`, `mutable`, `unknown` + `basis` | chú thích của dự án có rationale; instance evidence (statement có P580/P582, nhiều statement theo thời gian) | **không** từ `cardinality_constraint` |
| `temporal_overlap` | statement × passage × question | `overlap`, `disjoint`, `unknown` | P580/P582/P585 kèm precision; mốc thời gian trong câu hỏi/passage | thiếu khoảng thời gian ⇒ `unknown`, không phải `overlap` |
| `qualifier_evidence` | statement | tập qualifier PID, rank, số reference | full statement (`p:/ps:/pq:`) | — |
| `entity_identity` | mention × entity | `same`, `different`, `unknown` + loại evidence (`qid`, `label`, `alias`, `historical_name`, `redirect`, `type_mismatch`) | labels/aliases, P1448/P1449 kèm thời gian, P31 | trùng label **không** suy ra `same` |
| `relation_semantics` | (p_question, p_passage) | `same`, `inverse`, `subproperty`, `related_different`, `unrelated`, `unknown` | P1696, Q21510855, P1647 | — |

**Mutability và cardinality là hai chiều độc lập.**
- Cột cardinality lấy từ **constraint thật** trong Wikidata reference slice (§2.1; manifest
  `manifests/wikidata_reference_slice.json`, rev = `lastrevid` của property).
- Cột mutability là **nhận định làm việc**, chưa phải nhãn. Nhãn sẽ do dự án tự chú thích, kèm rationale.

|  | stable (thường không đổi theo thời gian) | mutable (đổi theo thời gian) |
|---|---|---|
| **single-best-value khai báo** | P19 place of birth: **single-best-value** (không phải single-value), status **suggestion**, 1 exception, separator P3831 (rev 2561664064); P569 date of birth: single-best-value, suggestion | P6 head of government: single-best-value (status thường), 9 separator gồm P580/P582, có required-qualifier (rev 2562704323) |
| **không khai báo cardinality** | P161 cast member: **không** có multi-value constraint (rev 2562933347), dù trang help lấy P161 làm ví dụ property "usually have many values" | P26 spouse: symmetric + contemporary, không có cardinality (rev 2562714916); P54 member of sports team: không có cardinality (rev 2559207125) |

→ Cả bốn ô đều có ví dụ thật. Không thể suy mutability từ cardinality, và ngược lại.

Khái niệm mutable/stable có trong When Facts Change: paper dùng 27 mutable relations, ví dụ "member of sports
team" [paper p.1, p.4]. Paper này gắn mutable triple với việc **có** temporal qualifier [p.4]; thiết kế ở đây
tách hai thứ đó thành hai signal. **Không** copy danh sách `MUTABLE_PROPERTIES` / `STABLE_PROPERTIES` của repo đó
(repo không có LICENSE). Nhãn mutability của dự án phải tự chú thích, kèm rationale.

### 2.1 Kiểm chứng trên Wikidata reference slice (2026-11-04)

Slice gồm:
- 200 ID: 29 property, 8 entity seed lấy đủ statement, 163 item mô tả nhẹ qua WDQS;
- 498 statement, 1,06 MB lưu (gzip).

Script: `scripts/wikidata/build_reference_slice.py`. Mọi request có URL, thời điểm, sha256 trong manifest.
Dữ liệu là **live** tại thời điểm tải; mỗi entity/property được pin bằng `lastrevid`.

- **Cardinality.**
  - Chỉ 2/29 property mang **single-value** (Q19474404): P1696 và P585.
  - 11/29 mang **single-best-value** (Q52060874): P19, P20, P22, P25, P35, P36, P569, P570, P580, P582, P6.
  - P19, P20, P569, P570 có status **suggestion**.
  - Số exception lên tới 25 (P22), 15 (P36), 10 (P25).
  - → Rule kiểu "single-value ⇒ contradiction" thậm chí không áp dụng được cho phần lớn property quan hệ:
    chúng khai báo "best value", không khai báo "single value".
- **Tài liệu ≠ dữ liệu.**
  - Trang Single value lấy P19/P20 làm ví dụ, nhưng P19/P20 hiện là single-best-value (suggestion).
  - Trang Multi value nhắc P161, nhưng P161 không có multi-value constraint.
  - Signal phải đọc từ property entity (có pin revision), không từ trang help.
- **Inverse.**
  - P22 ↔ P40 được khai báo qua inverse constraint Q21510855 + P2306 (không qua P1696).
  - P40 có P1696 = P8810.
  - P26 tự inverse (P1696 = P26) và symmetric.
  - → `relation_semantics` phải đọc **cả hai** cơ chế.
- **KG tự mâu thuẫn về ranh giới thời gian.** Ho Chi Minh City (Q1854, rev 2563461668) có tên chính thức
  (P1448) "Saïgon"@fr kết thúc 1975-04-30, "Сайгон"@ru kết thúc 1976-07-01, "Sài Gòn"@vi kết thúc 1976-07-02.
  → `temporal_overlap` gần ranh giới phải là `unknown`, không ép thành `overlap`/`disjoint`.
- **Homonym.**
  - Paris (Q90) và Paris, Texas (Q830149) có tập P31 (truthy) **không giao nhau**, dù cả hai đều là city
    qua P279.
  - Kiểm tra P31 nông (không suy luận P279) là evidence yếu.
- **Alias mơ hồ.** Q1854 có alias "Ho Chi Minh", cũng là tên một người. Trong view nhỏ, kiểm tra "alias dùng
  chung" không phát hiện được vì entity người không có trong view.
- **Reproducibility.** Tải lại `Special:EntityData/Q1156.json?revision=2562604813` cho nội dung **giống hệt từng
  byte** bản tải đầu → pin theo revision là cơ chế tái lập khả thi cho slice.
- **Rate limit.**
  - Lần chạy 1: WDQS trả **429** hai lần (04:24:57Z, 04:25:30Z) cho query mô tả item → builder dừng, không
    bypass.
  - Lần chạy 2: dùng lại 9 response đã lưu, lấy property trước, WDQS trả 200.
  - Cả hai lần đều ghi trong manifest (`annotations`).

## 3. DBpedia `infobox-properties` — trả lời câu hỏi 4

Lưu ý phạm vi bằng chứng:
- `downloads.dbpedia.org` bị **connection reset** (00_environment §4), nên **không** kiểm được file release.
- Bằng chứng gồm ba nguồn:
  - Databus metadata (JSON-LD);
  - mã nguồn DBpedia Information Extraction Framework (DIEF), clone partial và sparse vào `third_party/`, HEAD
    `b66cb8b9`, commit 2026-09-28;
  - SPARQL trên endpoint **live** `https://dbpedia.org/sparql`.
- Endpoint live có thể khác release 2022.12.01.

### 3.1 Raw/generic hay mapping-based? → **generic (raw)**

- Databus group `dbpedia/generic`:
  - title "Wikipedia Extraction with Generic Parsers";
  - abstract "Structured data from Wikipedia extracted by the several Generic Extractors from the DBpedia
    Information Extraction Framework (DIEF)";
  - artifact gồm `infobox-properties`, `infobox-property-definitions`, `labels`, `redirects`, `disambiguations`, …
- Group `dbpedia/mappings` ("Wikipedia Extraction using MappingExtractor") chứa `instance-types`,
  `mappingbased-objects`, `mappingbased-literals`, … — tức là type và mapping-based facts nằm **ở group khác**.
- Version 2022.12.01 của `infobox-properties`:
  - title "Extracted facts from Wikipedia Infoboxes";
  - description: "Data from Wikipedia's infoboxes, as is with some smart automatic (generic) parsing. This dataset
    has the best fact coverage, but has less consistency than the cleaned mapping infobox dataset.";
  - license `cc-by3.0`.
- Mã nguồn: `InfoboxExtractor` khai báo ba dataset `InfoboxProperties`, `InfoboxTest`, `InfoboxPropertyDefinitions`:
  `datasets` (`third_party/dbpedia-extraction-framework/core/src/main/scala/org/dbpedia/extraction/mappings/InfoboxExtractor.scala:106`).

### 3.2 Chứa thông tin gì?

Mỗi tham số infobox được ghi thành **một** triple `dbp:<key dạng camelCase>`. Mỗi quad mang `sourceIri` làm context:
`InfoboxProperties` (`third_party/dbpedia-extraction-framework/core/src/main/scala/org/dbpedia/extraction/mappings/InfoboxExtractor.scala:145`).

Hàm đổi key sang camelCase, rồi **xóa số ở cuối**; chú thích trong code là "Rename Properties like LeaderName1,
LeaderName2, ... to LeaderName":
`getPropertyUri` (`third_party/dbpedia-extraction-framework/core/src/main/scala/org/dbpedia/extraction/mappings/InfoboxExtractor.scala:289-300`).
Regex là `[0-9]+$`:
`TrailingNumberRegex` (`third_party/dbpedia-extraction-framework/core/src/main/scala/org/dbpedia/extraction/config/mappings/InfoboxExtractorConfig.scala:31`).

Định nghĩa property chỉ gồm `rdf:type` và `rdfs:label`:
`InfoboxPropertyDefinitions` (`third_party/dbpedia-extraction-framework/core/src/main/scala/org/dbpedia/extraction/mappings/InfoboxExtractor.scala:166-167`).

Giá trị được parse heuristic: unit, số, ngày, toạ độ, link, string (`extractValue` và các hàm sau nó).

Ví dụ từ endpoint live (2026-11-04T03:46:56Z):
- `dbr:Tokyo dbp:leaderName` có 3 giá trị `11`, `42` (integer) và `"Yuriko Koike"`;
- `dbp:leaderTitle` có 3 giá trị (House of Councillors, House of Representatives (Japan), Governor of Tokyo);
- **cặp title ↔ name bị mất**, và các con số 11/42 (khả năng là số ghế) nằm lẫn trong `leaderName`.

### 3.3 Bảng kiểm

| Câu hỏi | `infobox-properties` | Bằng chứng | Ở chỗ khác trong DBpedia? |
|---|---|---|---|
| Entity types | ❌ | không thuộc dataset này | `mappings/instance-types` (rdf:type theo DBpedia ontology) |
| Class hierarchy | ❌ | — | DBpedia ontology (`rdfs:subClassOf`) |
| Domain/range của property | ❌ cho `dbp:` | `ASK` có `dbp:` property nào mang `rdfs:domain` → `false`; `rdfs:range` → `false` (03:46:43Z, 03:46:46Z) | `dbo:`: 2.494 property có `rdfs:domain` (03:46:51Z) |
| Alias / tên lịch sử | ⚠️ một phần, dạng literal không định kiểu | `dbr:Ho_Chi_Minh_City`: `dbp:otherName "Saigon"`, `dbp:officialName`, 4 `dbp:nickname`; `dbr:Mumbai`: `dbp:otherName "Bombay"` (03:53:12Z, 03:53:17Z). Không phân biệt alias với tên lịch sử, không có thời gian hiệu lực | `generic/redirects`: `dbr:Saigon dbo:wikiPageRedirects dbr:Ho_Chi_Minh_City` → `true` (03:53:15Z) |
| Cardinality constraint tường minh | ❌ | — | ontology: chỉ 30 `dbo:` property là `owl:FunctionalProperty` (03:46:49Z) — đây là axiom OWL, không có exception/status như Wikidata |
| Temporal qualifier kiểu P580/P582/P585 | ❌ | key đánh số bị gộp (`TrailingNumberRegex`); key như `term_start` (nếu có) chỉ thành một triple riêng, không gắn với giá trị nó mô tả | không có tương đương statement-level |
| Statement-level provenance / qualifier / rank | ❌ trong file phát hành | extractor có gắn `sourceIri` (line 145), nhưng cả 138 part của release 2022.12.01 đều là `ttl.bz2`. Turtle không có slot context nên provenance không nằm trong file (**suy luận từ định dạng**) | — |

### 3.4 Phiên bản bạn đã dùng

- Trên Databus, version **mới nhất** của `infobox-properties` là **2022.12.01**: issued 2022-12-01, modified
  2024-02-15. Các version trước gồm 2016.10.01 … 2022.09.01.
- Part tiếng Anh: `infobox-properties_lang=en.ttl.bz2`, `dcat:byteSize` 922.093.278, sha256 `6bd89440afb3f70b…`.
- Ngày "~2023-03-08" bạn nhớ **không trùng ID version nào** → **[UNVERIFIED]**. Có thể đó là ngày tải về, hoặc một
  bản build khác.
- File quá lớn cho cloud (922 MB > ngân sách 50 MB). Host tải về cũng bị chặn.

## 4. Paper đã audit dùng KG/corpus gì?

"Wikidata (trực tiếp)" = paper tự truy vấn/parse Wikidata. "Gián tiếp" = dùng dataset do người khác xây từ Wikidata.

| Paper | Dữ liệu chính | KG có cấu trúc | Vai trò của Wikidata | Bằng chứng |
|---|---|---|---|---|
| MAGIC | benchmark conflict sinh từ KG | **Wikidata5M**; ví dụ sơ bộ từ DBpedia và YAGO | **trực tiếp**: source KG để sinh benchmark | p.3; DBpedia/YAGO p.10, p.16–18 (Table 14) |
| When Facts Change | benchmark mutable/stable facts | **Wikidata dump** | **trực tiếp**: parse dump để sinh benchmark | p.1, p.2, p.4 ("parsing a recent Wikidata dump"), p.20 |
| TimeR4 | MultiTQ (ICEWS05-15), TimeQuestions | ICEWS (temporal KG); Wikidata qua TimeQuestions | gián tiếp: dataset; tác giả nêu LLM "pretrained on the Wikidata knowledge graph corpus" | p.4–6 |
| Relink | 5 benchmark multi-hop, gồm 2WikiMultiHopQA, HotpotQA, MuSiQue | graph tự xây | gián tiếp qua 2Wiki | p.5 |
| MemGraphRAG | HotpotQA, 2WikiMultiHopQA, MuSiQue | graph tự xây | gián tiếp qua 2Wiki | p.6 |
| ContextConflict | ConflictBank, CONFLICTS, SciFact, … | — | gián tiếp qua ConflictBank (Ragability mô tả ConflictBank "based on 2.86M claims extracted from Wikidata", p.1) | p.3 |
| Ragability | WikiContradict (Wikipedia) + entity hư cấu | — | chỉ nhắc ConflictBank trong related work | p.1–2 |
| TruthfulRAG | FaithEval, MuSiQue, SQuAD, RealtimeQA | graph do LLM trích từ text | không | p.4 |
| EvoTrustRAG | FaithEval, MuSiQue, SQuAD, RealtimeQA (Track A) | — | không | p.4 |
| GraphRAG-Bench | tiểu thuyết + medical guidelines | graph tự xây | không | p.5 |
| CONFLICTS (Cattan et al.) | query + kết quả Google Search | — | không | p.2, p.4 |
| Khatri et al. (typing) | CONFLICTS | — | không | p.2 |
| ArbGraph | LongFact, RAGChecker; retrieval Wikipedia cố định | graph tự xây | không | p.11–12 |
| HVM-GraphRAG | MMLongBench, M3DocVQA (tài liệu HTML lấy từ Wikipedia), Qasper | graph tự xây | không | p.6 |
| ProStruct-RAG | CLARKNews, StreamingQA (bài báo web) | proposition graph | không | p.5–6 |
| PAGE-RAG | 2 cuốn sách + UltraDomain-Mix | graph tự xây | không | p.12 |
| ConflictRAG | Natural Questions | — | không | p.6 |
| Survey | (tổng quan) | — | không nhắc | — |

Đếm chuỗi "Wikidata" trong bản pdftotext của từng paper: MAGIC 12, When Facts Change 10, TimeR4 3, Ragability 1,
14 paper còn lại 0 (đếm thô, chỉ để đối chiếu). **2WikiMultiHopQA** được xây bằng Wikidata. Abstract arXiv 2011.01060
(tải 2026-11-04T03:48:37Z) viết: "We also exploit the structured format in Wikidata and use logical rules to create
questions" → rủi ro leakage khi method tra Wikidata.

Kết luận trung thực:
- Wikidata là KG **phổ biến nhất trong nhóm paper có dùng KG có cấu trúc để xây benchmark conflict/temporal**
  (MAGIC, When Facts Change, TimeQuestions, ConflictBank).
- Nhưng **đa số** paper trong audit không dùng KG có cấu trúc nào; họ tự xây graph từ text.
- DBpedia chỉ xuất hiện như ví dụ sơ bộ trong MAGIC.

## 5. A / B / C — khuyến nghị và các lần thử falsify

### 5.1 Chấm theo tiêu chí (định tính; "+" là lợi, "−" là bất lợi)

| Tiêu chí | A: chỉ Wikidata | B: chỉ DBpedia `infobox-properties` | C: cả hai |
|---|---|---|---|
| Hợp với G2⁺ (6 signal ở §2) | + có đủ 6 signal | − thiếu cardinality, temporal, qualifier, type; identity chỉ một phần | + nhờ A |
| Độ giàu schema | + constraint, type, inverse, subproperty | − chỉ `rdf:type rdf:Property` + label cho `dbp:` | + |
| Temporal / qualifier | + P580/P582/P585, rank | − không có | + nhờ A |
| Reproducibility | − live; cần pin revision hoặc dump | + release có version + sha256 trên Databus (nhưng host tải bị chặn trong cloud) | − phải pin hai nguồn |
| Công sức implement | trung bình | thấp cho triple; **cao** nếu muốn tự dựng lại type/alias | cao nhất |
| Rủi ro answer leakage | − **cao** (2Wiki, ConflictBank, TimeQuestions xây từ Wikidata) | − cũng cao: infobox lấy từ chính các trang Wikipedia mà 2Wiki dùng làm context | − như A |
| Novelty | dùng Wikidata tự nó không mới; điểm mới (nếu có) là dùng constraint làm soft evidence để typing apparent/genuine trong reranking — **[UNVERIFIED]**, cần literature search có hệ thống ở Phase C | thấp cho G2⁺ | cross-KG có thể thêm một góc phân tích |
| Liên tục với luận án (Journal 1–2 dùng DBpedia) | − | + | + |

### 5.2 Các lần thử falsify default ("Wikidata chính; DBpedia là thí nghiệm phụ tùy chọn")

| # | Giả thuyết đối lập | Kết quả |
|---|---|---|
| F1 | "DBpedia `infobox-properties` đủ cho G2⁺, nên chọn B" | **Bác bỏ**: thiếu 4/6 signal (§3.3). B chỉ hỗ trợ một biến thể yếu (identity qua `otherName`/redirects; granularity thô qua `subdivisionName`). |
| F2 | "Leakage với Wikidata nghiêm trọng đến mức nên bỏ Wikidata" | **Không bác bỏ được A**, nhưng là threat thật. DBpedia cũng rò rỉ (cùng nguồn Wikipedia). Leakage là thuộc tính của *thiết kế đánh giá*, xử lý bằng §5.4, không bằng việc đổi KG. |
| F3 | "Reproducibility nghiêng về DBpedia" | **Đúng một phần**: Databus có version + sha256. Wikidata khắc phục được bằng pin revision từng entity (slice) và pin dump (MSI). Không đủ để đổi lựa chọn core. |
| F4 | "Thí nghiệm signal-availability cần DBpedia" | **Bác bỏ một phần default**: ablation "chỉ dùng các signal DBpedia có" làm được ngay trong Wikidata bằng cách tắt signal. Giá trị **riêng** của DBpedia chỉ còn: (i) schema và lỗi extraction khác (generalization cross-KG), (ii) liên tục luận án. |
| F5 | "C ngay từ đầu tốt hơn" | **Bác bỏ**: tăng gấp đôi công sức trước khi hypothesis core được kiểm. Nhánh DBpedia không kiểm được temporal/cardinality nên không giúp falsify core. |
| F6 | "Novelty đến từ việc dùng Wikidata" | **Bác bỏ** cách đóng khung này: novelty (nếu có) nằm ở *cách dùng* constraint như evidence mềm trong reranking, chưa kiểm literature. |
| F7 | "Nhánh DBpedia chỉ cần `infobox-properties` như Journal 1–2" | **Bác bỏ**: thiếu type/alias/ontology nên không so sánh công bằng. Cần thêm `mappings/instance-types`, `generic/redirects`, ontology. |

### 5.3 Khuyến nghị

**A cho core, cộng nhánh C-staged có điều kiện.**

1. Phase B–C và claim chính của paper dùng **Wikidata**: tiny slice trong cloud; dump pin ngày + sha256 trên MSI.
2. Nhánh DBpedia được **đăng ký trước**, chỉ chạy khi core đạt tiêu chí, phạm vi nhỏ:
   - cùng pool, cùng nhãn;
   - G2⁺ chỉ dùng signal DBpedia có;
   - báo cáo như generalization/continuity, **không** phải bằng chứng chính.
3. Ablation "signal availability" làm trong Wikidata (tắt từng signal), không cần DBpedia.

So với default của bạn, có 3 sửa đổi:
- (i) nhánh DBpedia dùng generic + mappings + ontology, không chỉ `infobox-properties`;
- (ii) ablation signal làm trong Wikidata;
- (iii) bắt buộc protocol leakage ở §5.4.

**Điều kiện làm đổi khuyến nghị:**
- nếu trên MSI không pin được Wikidata (dump không tải được, revision không lấy lại được) → xem lại reproducibility;
- nếu G2⁺ chỉ thắng ở setting KG-oracle → claim phải thu hẹp lại.

### 5.4 Protocol chống circularity / leakage (đưa vào PLAN)

- **Setting KG tách bạch.** Báo cáo riêng từng setting, không gộp:
  - **S0** không KG;
  - **S1** schema-only: metadata và constraint của property;
  - **S2** S1 + identity: label, alias, P31 của entity được nhắc trong passage;
  - **S3** KG-oracle: full statements, kể cả (s, p) của câu hỏi — chỉ là **upper bound**.
- **Masking.** Trong S1/S2, view KG không chứa statement `(s, p_question, ·)` của chính câu hỏi.
- **Tách nhãn khỏi method.** Nhãn của perturbation synthetic được sinh từ Wikidata, nên tập synthetic chỉ là
  **capability probe**. Bằng chứng chính phải đến từ tập có **nhãn độc lập với KG**:
  - CONFLICTS, Ragability, và/hoặc một tập nhỏ do bạn chú thích theo codebook;
  - nhãn mức passage, có báo cáo agreement nếu có annotator thứ hai.
- **Báo cáo riêng** theo nguồn dữ liệu: dựng từ Wikidata hay không.

### 5.5 Reproducibility cho Wikidata

- WDQS là live và có lag → chỉ dùng cho **selection**.
- Dữ liệu statement lấy từ `Special:EntityData/<ID>.json`. Manifest ghi:
  - `lastrevid`;
  - thời điểm;
  - URL chính xác;
  - sha256.
- Đã kiểm (§2.1): tải lại theo `?revision=<lastrevid>` cho response giống hệt từng byte.
- Trên MSI: dùng JSON dump có ngày cố định + sha256 thay cho truy vấn live.

## 6. Mục [UNVERIFIED] / giới hạn

- Ánh xạ "infobox-properties lang=en ~2023-03-08" sang version Databus.
- Nội dung file release DBpedia: host tải về bị connection reset. Kết luận về provenance trong file là suy luận từ định
  dạng `ttl`.
- Kết quả SPARQL lấy từ endpoint **live**, không phải release 2022.12.01.
- ~~Constraint thực tế của P6, P26, P54~~ → đã kiểm bằng slice (§2, §2.1). Nhãn mutability vẫn chưa có.
- Licence **dữ liệu** 2WikiMultiHopQA:
  - repo `Alab-NII/2wikimultihop` (HEAD `13800e5b`, sparse checkout chỉ `LICENSE` + `README.md`) có file LICENSE
    Apache-2.0;
  - README không nêu licence riêng cho data (phân phối qua link ngoài);
  - bản 500 ví dụ dùng ở đây lấy từ fork Relink (MIT) `data/wikiMQA/dataset/samples.json`, sha256
    `dde3427d731b2155…`.
- Cách MuSiQue/HotpotQA được xây: chưa kiểm trong session này.
