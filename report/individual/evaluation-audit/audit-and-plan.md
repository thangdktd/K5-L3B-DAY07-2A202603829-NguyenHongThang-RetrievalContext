# Day 07 — Audit offline, checklist và kế hoạch B–E

Phạm vi hoàn thành: **chỉ giai đoạn A**. Không gọi OpenAI API, không chạy lại
retrieval/Agent/unit tests, không phát triển validator, không chạy TEST, không
commit/push. Chỉ đọc tài liệu/artifacts, kiểm tra hash và tính dự toán. Tra cứu
trang giá chính thức qua web không phải request inference OpenAI.

Đã đọc README.md, BENCHMARK.md, RUBRIC.md, RULES.md, SUBMISSION.md,
REPORT_TEMPLATE.md và report/individual/README.md. Không tự chấm hoặc bảo đảm
đạt 85 điểm; dưới đây là bằng chứng và phần còn thiếu của rubric cơ bản.

## 1. Kết quả có thể tái sử dụng

- 292 chunks cấu hình B, 20 questions answerable và 24 cases: 17 DEV / 7 TEST.
  Manifest schema day07-evidence-groups-v2, freeze 2026-11-16 10:55:58 +07:00.
  Hash corpus/nhãn/generator/evaluator/documentation đều khớp manifest.
- Corpus là 38 trang nội dung vật lý 4–41 từ PDF Daikin 48 trang, revision
  2025.11. Không được gọi toàn bộ PDF là corpus đã index. Embedding local
  all-MiniLM-L6-v2, 384 chiều; pgvector Day06, đúng run/config B; fingerprint và
  snapshot database đã có trong traces, không cần kết nối DB trong audit này.
- Day06 provenance ghi local lab được người dùng cho phép; quyền public
  redistribution/full-text GitHub và kênh cấp nguồn cho người chấm chưa xác nhận.
  Không tự tuyên bố license mở hoặc tự tạo URL tải gốc. Khi chuẩn bị nộp cần
  ghi cách cấp quyền/tái tạo; không cần giải quyết bằng publish trong audit này.
- 120 traces retrieval = 4 phương pháp × 2 budgets × 15 DEV answerable. Các tổng
  Hit@1/Hit@3/Context đã được đối chiếu lại từ traces với metrics; các hashes trong
  checkpoint3a/verification.json đều khớp. Đây là kiểm tra artifacts, không rerun.
- 77/77 unit tests là kết quả đã đo ở lần sửa grounding trước; audit không chạy lại.

| Phương pháp | Budget ký tự | Hit@1 | Evidence Hit@3 | Context Evidence | Median ms |
|---|---:|---:|---:|---:|---:|
| TF-IDF | 800 | 10/15 (66,7%) | 13/15 (86,7%) | 7/15 (46,7%) | 3,45 |
| Dense | 800 | 12/15 (80%) | 13/15 (86,7%) | 7/15 (46,7%) | 42,32 |
| BM25 | 800 | 12/15 (80%) | 14/15 (93,3%) | 6/15 (40%) | 5,46 |
| Hybrid RRF | 800 | 11/15 (73,3%) | 15/15 (100%) | 7/15 (46,7%) | 44,52 |
| TF-IDF | 2400 | 10/15 (66,7%) | 13/15 (86,7%) | 13/15 (86,7%) | 2,39 |
| Dense | 2400 | 12/15 (80%) | 13/15 (86,7%) | 13/15 (86,7%) | 38,07 |
| BM25 | 2400 | 12/15 (80%) | 14/15 (93,3%) | 14/15 (93,3%) | 3,41 |
| Hybrid RRF | 2400 | 11/15 (73,3%) | 15/15 (100%) | 15/15 (100%) | 57,32 |

Cùng corpus, nhãn, query gốc, top3, không filter; budget gồm header và separators.
Latency là warm search + packing, không gồm khởi tạo model/query encoding. Một
lần chạy local, không phải thống kê latency ổn định. Chi phí dịch vụ retrieval $0;
không suy ra local compute miễn phí. Context 3A là proxy chưa gửi LLM.

Context Agent 3B dùng header compact source_id/page/id và ưu tiên kết quả mới;
khác header source path/packing append của 3A. Vì vậy 15/15 context của 3A không
được dùng thay số Context Evidence Rate Agent trên 17 DEV chưa đo.

## 2. Audit Agent: phân biệt kết quả và phiên bản

| Artifact | Câu | Kết quả cuối | Phân loại | Requests | Input/output tokens |
|---|---|---|---|---:|---|
| checkpoint3b-pilot | q01 | error, HTTP401 | Provider/authentication | 1 | Không được trả usage |
| checkpoint3b-pilot-02 | q01 | error, timeout42,49s | Provider/transport | 1 | Không được trả usage |
| checkpoint3b-q01-01 | q01 | abstain | Validator: thiếu inline citation | 2 | 1531 / 107 |
| checkpoint3b-q01-02 | q01 | answered, 2/2 | Citation đúng, evidence đủ | 2 | 2053 / 138 |
| checkpoint3b-q12-01 | q12 | abstain | Validator: citation thiếu/không đồng bộ | 2 | 2126 / 200 |
| checkpoint3b-q12-02 | q12 | abstain | Validator: paraphrase không qua exact span | 2 | 1958 / 174 |

Chưa có trace Agent unanswerable DEV. Chưa quan sát được trường hợp model chủ động
abstain vì thiếu evidence trong corpus. Các abstention hiện có là validator từ
chối trên câu answerable, không được tính là từ chối đúng câu thiếu bằng chứng.
API/provider error không phải abstention; báo riêng và không biến thành điểm 0
của một câu model đã trả lời thành công. Case chưa chạy không có output/điểm.

q01 PASS dùng schema answer/citations cũ, max2 searches; q12 mới nhất dùng
structured claims, max3 searches. Cả hai trước bản grounding deterministic mới.
Không trace nào khớp toàn bộ code hiện tại. Hash đầy đủ từng lần chạy/config nằm
trong audit_inventory.json; không gộp q01 PASS và q12 FAIL thành một điểm của
cấu hình hiện tại, không chọn trace thuận lợi rồi gọi đó là cùng một experiment.

Có thể tái sử dụng q01-02 và q12-02 như hai kết quả lịch sử đã chấm, giữ bảng
phiên bản riêng. Không chạy lại chỉ để đổi kết quả. 15 case còn thiếu:
q02–q11, q13–q15, q_unans_dev_01 và q_unans_dev_02 (13 answerable, 2 unanswerable).

Khi chấm thủ công: có thể ghi claim đề xuất của q12 có support, nhưng output cuối
thực tế vẫn abstain → grounded grade0 và false abstention. Không thay output,
render lại claim cũ hoặc chuyển thành answered để tăng điểm. Ghi riêng:
(1) chất lượng output cuối, (2) semantic support của proposal, (3) lý do validator.

Các code cũ chỉ còn hash và request/output traces, chưa có đầy đủ source snapshot
cho từng revision không commit. Hash không tự khôi phục source. Đây là hạn chế tái
lập lịch sử phải nêu, không khắc phục bằng chạy lại. Cấu hình tương lai cần lưu
snapshot code/config/env trước khi inference, không cần commit.

## 3. Checklist rubric cơ bản 85 điểm

| Hạng mục | Đã có | Còn thiếu / chưa hoàn tất |
|---|---|---|
| Dữ liệu & benchmark — 13 | Corpus, provenance, Day06 vector identity, 24 cases/freeze, AND/OR q12, absence audit | Chốt kênh nguồn/quyền chia sẻ cho người chấm; mô tả extraction/table limits |
| Retrieval — 17 | 4 phương pháp, Dense pgvector thật, 8 configs, traces/score/source/metadata, DEV metrics | Đưa bảng và điều kiện vào báo cáo cá nhân; không rerun |
| Agent & context — 17 | OpenAI function calling thật, Hybrid, bounded context/dedup, trace và lỗi | 15 DEV còn thiếu; kiểm tra thực tế unanswerable/multi-search; một cấu hình cuối có version rõ |
| Đánh giá — 17 | Retrieval/context proxy; review q01/q12 có lý do | Nhãn từng câu/citation cho DEV còn thiếu; tổng hợp theo phiên bản; abstention chưa đo; toàn bộ TEST còn cấm |
| Thử nghiệm & cải thiện — 13 | Ít nhất hai cải thiện retrieval/context, nhiều lỗi và before/after | Chốt lựa chọn Agent sau DEV, tiêu chí trước TEST; chưa có matched Agent comparison đủ DEV |
| Tái lập & báo cáo — 8 | Code, SDK/dependencies, README, hashes, nhiều báo cáo phụ | Báo cáo đúng tên; source/config snapshots; artifact index; quyền truy cập grader; TEST/reviews còn thiếu |

Submission chưa có report/individual/2A202603829_NguyenHongThang.md.
REPORT_TEMPLATE.md và MSSV_HoTen.md mới là mẫu trống, không phải bài nộp hoàn chỉnh.
Các file code/data/artifacts chủ yếu chưa tracked; không stage/commit/push trong
nhiệm vụ này. .env và .env.local được Git ignore. Quét định dạng key/Bearer dài
trong src/report/tests không phát hiện match; đây không phải chứng nhận tuyệt đối
không có dữ liệu nhạy cảm. Full-text traces còn phụ thuộc quyền phân phối nguồn.

## 4. Kế hoạch B — DEV, chỉ thực hiện sau phê duyệt

1. Chuẩn bị runner resume với allowlist đúng 15 ID thiếu, refuse duplicate case,
   resume manifest và per-case checkpoint. Không dùng ngay runner mặc định: nó sẽ
   gọi lại17 câu, output900 tokens và timeout45s. Chưa sửa runner trong giai đoạn A.
2. Đề xuất cấu hình chung cho batch thiếu: gpt-4.1-mini, Hybrid candidate20/k60,
   top3, budget2400, structured claims hiện tại, max3 searches/4 model calls,
   output250/request, timeout60s, retries0. Không đổi validator nữa. Snapshot/hash
   source, prompt/schema, model identity và env; gold chỉ dùng sau inference.
3. Dừng batch khi provider/protocol error; không retry. Giữ các case chưa chạy là
   not_run và không tự gọi tiếp/restart. Approval budget không phải lệnh retry.
4. Reuse q01-02/q12-02 nguyên trạng trong historical manifest. Báo riêng cohort
   mới15 cases và các cohort cũ. Không có phép tổng hợp này thành homogeneous
   DEV17 của cấu hình hiện tại. Nếu sau này cần DEV17 cùng một version, phải báo
   thiếu và xin phép riêng; không tự chạy lại q01/q12 có trace hợp lệ.
5. Chấm trực tiếp từng answer/context/citation: final grounded0/1/2, citation
   support từng ID, answer citation coverage, tool use/search distribution,
   abstention/false abstention, context evidence AND/OR. Báo n/N đúng cohort;
   provider errors/not_run báo riêng. Không gọi LLM judge. Người dùng nên xác nhận
   các nhãn do assistant review để phân biệt với independent human grading.
6. Giữ output cuối khi validator reject. Có cột proposal/manual support và cột
   rejection_type; không đổi output/gold/validator, không post-hoc render như thật.

### Dự toán xin duyệt, chưa gọi API

Đơn giá kiểm tra ngày 2026-11-16 tại
https://developers.openai.com/api/docs/models/gpt-4.1-mini : input$0.40,
cached input$0.10, output$1.60 /1M tokens. Không gọi API để kiểm tra giá/model.

- 15 cases × tối đa(3 searches+1 finish) = **60 requests**; output tối đa15000
  tokens nếu mọi request dùng hết250. Lượt SDK success/error đều tiêu ngân sách
  request; không dùng thêm request để kiểm tra key/model hay retry.
- Các phiên hợp lệ đã đo thường2 requests/case; token charge khoảng$0.00104–
  $0.00117/case. Ước tính batch15 khoảng**$0.016–$0.04** tùy số follow-ups.
- Kịch bản dự phòng: 60 requests ×4000 input tokens/request (giả định lập kế hoạch,
  chưa phải cap) =240000 input; cộng15000 output → **$0.12**. Đề xuất reserve
  **$0.15**, không phải trần billing tuyệt đối. Runner hiện chưa chặn input/cost;
  giai đoạn B cần kiểm tra/stop gate trước khi vượt ngân sách dự kiến, không gọi
  endpoint đếm token. Không assert usage/cost của timeout là0.
- Dự toán trên chỉ dành cho15 case thiếu, không bao gồm matched baseline Agent
  hoặc TEST. Một baseline Agent17 cases riêng có thể thêm tối đa68 requests;
  chỉ cân nhắc khi cần thiết và phải xin dự toán/phê duyệt khác, không tự chạy.

## 5. Kế hoạch C — so sánh và chọn

Không cần API mới để chứng minh hai cải thiện retrieval theo template:
- TF-IDF800 → BM25 cùng800: Hit@3 13/15→14/15, Hit@1 10/15→12/15, context
  7/15→6/15 (cải thiện ranking nhưng context giảm; phải báo cả kết quả giảm).
- Hybrid800 → Hybrid2400: ranking giữ nguyên15/15 Hit@3, context7/15→15/15;
  số ký tự context trung bình569.1→1929.9. Không suy ra answer quality từ proxy.
- RRF so với Dense/BM25: Hit@3 tăng nhưng Hit@1 Hybrid thấp hơn và latency cao hơn.

Đủ điều kiện để chọn retrieval tạm thời Hybrid2400. Chưa đủ matched Agent data
để tuyên bố cấu hình Agent tốt nhất hoặc cải thiện Agent trên DEV17. q01 và q12
không phải same-query A/B dưới một version; không thay bằng retrieval metrics.

Sau B mới chốt config Agent cuối trước TEST, dùng tiêu chí công bố trước: grounded
answer/2, citation support và false abstention, context coverage; tie-break token
cost/latency. Không tối ưu bằng TEST. Lưu lock JSON + hashes + source snapshot;
TEST yêu cầu khớp lock và manifest. Audit hiện chỉ ghi hash inventory, không tự
coi đó là final lock hoặc thay đổi benchmark freeze.

## 6. Kế hoạch D — TEST, tuyệt đối chưa chạy

Chỉ chuẩn bị sau DEV/chốt cấu hình và chưa có API call khi chuẩn bị. Chuẩn bị
runner7 cases với guard yêu cầu phê duyệt riêng và final lock; bảng chấm trống
cho5 answerable/2 unanswerable, không điền output hay điểm. Không đọc TEST để tune.

BENCHMARK.md yêu cầu baseline và cấu hình chọn trên cùng TEST, không chỉ một
selected run. Cần định nghĩa baseline Agent rõ trước TEST (ví dụ TF-IDF800 với
cùng model/controller), quyết định so sánh DEV còn thiếu và trình phê duyệt chi
phí riêng. Không giả định TF-IDF retrieval offline đã thay cho baseline Agent.
Chấm context0/1/2 với lý do cho5 answerable mỗi config; grounded/citation/tool
use/abstention cho cả7, lỗi provider riêng. Lưu TEST một lần sau phê duyệt, không
retry tự động, không điều chỉnh hệ thống dựa trên TEST. Nếu TEST bị dùng để tune,
phải có TEST mới theo quy tắc; hiện không tạo hoặc thay gold.

## 7. Kế hoạch E — báo cáo cá nhân, chưa viết thay kết quả chưa có

Đường dẫn bắt buộc theo SUBMISSION + report/individual/README:
**report/individual/2A202603829_NguyenHongThang.md**, theo REPORT_TEMPLATE.md.

Các phần: dữ liệu/quyền/38 trang/292chunks, model384D+pgvector identity, benchmark
freeze/AND-OR/absence limits; bảng retrieval8configs; context engineering; OpenAI
Agent/schema/tools và xử lý lỗi; DEV theo cohort/version, reviewer và n/N; ít nhất
hai lỗi; before/after đã đo; latency/token/cost; hạn chế; lệnh chạy và artifact
index. Không làm bonus100trang. TEST ghi CHƯA CHẠY cho đến phê duyệt và đo thật.

Hai lỗi DEV chính đã đủ artifacts để viết, không cần rerun:
1. q01 đúng đáp án/evidence nhưng thiếu citation inline → validator false abstention;
   prompt/schema đã thử, q01 tiếp theo PASS. Chú thích input token1531→2053 tăng,
   không chỉ ghi chất lượng tăng; đây là hai revision đã quan sát.
2. q12 đủ hai nhóm nhưng flat citations thiếu nguồn; structured claims chọn đúng
   hai nguồn, vẫn bị extractive validator reject paraphrase. Giữ finalgrade0;
   tách semantic support của proposal. Bản deterministic sau đó mới unit-tested,
   chưa có live evidence; không tuyên bố q12 được sửa thành PASS.
Có thể bổ sung lỗi q05 budget skip correct chunk, q11 table scope từ3A.

Báo cáo đầy đủ vẫn phụ thuộc B và TEST sau phê duyệt. Không điền trung bình DEV17,
Agent unanswerable success, TEST scores hay independent human labels khi chưa đo.

## 8. Artifacts audit và điểm dừng

- audit_inventory.json: inventory, phiên bản/config/hash từng run, coverage, source
  hashes hiện tại, retrieval summary, budget assumptions và trường còn thiếu.
- Báo cáo này: đối chiếu rubric, các thiếu sót và kế hoạch B–E.
- Các traces/reviews/metrics lịch sử, Day06, source code, validator, benchmark,
  evaluator và template cá nhân được giữ nguyên trong audit.

**Dừng sau A. Chờ duyệt chuẩn bị B và ngân sách trước mọi DEV API request.**
