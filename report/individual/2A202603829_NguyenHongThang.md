# Báo cáo Day 7 – Nguyễn Hồng Thắng – 2A202603829

## 1. Dữ liệu và benchmark

- **Nguồn dữ liệu:** Tôi dùng tài liệu hướng dẫn lắp đặt và vận hành điều hòa Daikin VRV IV+, phiên bản 2025.11. File PDF có 48 trang; tôi sử dụng nội dung từ trang 4 đến trang 41 (38 trang). Dữ liệu đã được chia thành **292 chunks** ở bài Day 06. Tôi chỉ sử dụng cho bài thực hành. Quyền công khai toàn văn và quyền truy cập của người chấm vẫn cần được xác nhận.
- **Vector store:** PostgreSQL và pgvector, cơ sở dữ liệu `day6_lab`. Tôi dùng lại embedding `sentence-transformers/all-MiniLM-L6-v2` với **384 chiều**, không tạo embedding lại. Quá trình truy vấn chỉ đọc, không sửa dữ liệu Day 06.
- **Mô hình Agent:** OpenAI `gpt-4.1-mini`, dùng Responses API và gọi tool thật.
- **Benchmark:** Có **24 câu**, gồm **17 DEV** (15 câu có bằng chứng, 2 câu thiếu bằng chứng) và **7 TEST** (5 câu có bằng chứng, 2 câu thiếu bằng chứng). Tôi khóa benchmark trước khi đánh giá và kiểm tra hash sau khi chạy TEST.
- **Cách chấm:** Một câu có thể cần nhiều nhóm bằng chứng. `Hit@1` kiểm tra chunk đầu tiên có đủ các nhóm; `Evidence Hit@3` kiểm tra ba chunk đầu; `Context Evidence Rate` (CER) kiểm tra context cuối có đủ bằng chứng hay không. Các câu thiếu bằng chứng không tính vào mẫu số của ba chỉ số retrieval. Agent phải từ chối khi tài liệu không đủ thông tin.

File kiểm chứng: `data/benchmark_manifest.json`, `data/benchmark_validation.json`, `data/unanswerable_audit.json`.

## 2. Retrieval và thử nghiệm

Tôi thử TF-IDF, Dense, BM25 và Hybrid RRF trên cùng dữ liệu và câu hỏi. Các phương pháp đều lấy `top-k = 3`, không dùng metadata filter hoặc reranker. Hybrid RRF kết hợp kết quả Dense và BM25.

Tôi thử hai cách cải thiện:

- **Cải thiện 1:** Dùng Hybrid RRF với context tối đa **800 ký tự**, để kết hợp tìm kiếm theo từ khóa và ngữ nghĩa.
- **Cải thiện 2:** Tăng context của Hybrid RRF lên **2.400 ký tự**, để giữ được nhiều bằng chứng và điều kiện hơn.

### Kết quả Retrieval trên DEV

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian trung vị |
|---|---|---|---|---|---|---|---|
| Baseline | TF-IDF; top-3; không filter/rerank; 800 ký tự | Mốc so sánh | DEV | 10/15 (66,7%) | 13/15 (86,7%) | 7/15 (46,7%) | 3,45 ms |
| Phương pháp 2 | Dense pgvector; top-3; 800 ký tự | Tìm theo ngữ nghĩa | DEV | 12/15 (80,0%) | 13/15 (86,7%) | 7/15 (46,7%) | 42,32 ms |
| Phương pháp 3 | BM25; top-3; 800 ký tự | Tìm theo từ khóa | DEV | 12/15 (80,0%) | 14/15 (93,3%) | 6/15 (40,0%) | 5,46 ms |
| Cải thiện 1 | Hybrid RRF; top-3; 800 ký tự | Kết hợp Dense và BM25 | DEV | 11/15 (73,3%) | 15/15 (100%) | 7/15 (46,7%) | 44,52 ms |
| Cải thiện 2 | Hybrid RRF; top-3; 2.400 ký tự | Tăng context | DEV | 11/15 (73,3%) | 15/15 (100%) | 15/15 (100%) | 57,32 ms |
| Cấu hình đã chọn | Hybrid RRF; top-3; 2.400 ký tự | Chốt từ DEV, sau đó chạy TEST | TEST | 4/5 (80,0%) | 4/5 (80,0%) | 5/5 (100%) | Xem Agent bên dưới |
| Baseline | TF-IDF; top-3; 800 ký tự | So sánh trên TEST | TEST | 2/5 (40,0%) | 3/5 (60,0%) | 3/5 (60,0%) | Xem Agent bên dưới |

*Thời gian ở năm dòng DEV đầu là thời gian tìm kiếm và đóng gói context, chưa tính thời gian gọi LLM. Kết quả TEST trong bảng là từ lần chạy Agent thật. CER của Agent có thể tăng sau khi tìm kiếm bổ sung.*

**Hai lỗi tôi quan sát trên DEV:**

1. **q05:** Baseline với 800 ký tự bỏ sót điều kiện `30 mg/10 m`. Khi dùng Hybrid RRF và 2.400 ký tự, Agent nhận đủ bằng chứng và trả lời đúng. Điều này cho thấy context quá ngắn có thể làm mất thông tin quan trọng.
2. **q11:** Baseline lấy nhầm số liệu giữa các dòng của bảng điện. Hybrid tìm được dòng đúng nhưng bộ kiểm tra câu trả lời vẫn từ chối. Như vậy, tìm đúng bằng chứng chưa chắc đã tạo ra câu trả lời cuối cùng đúng.

Tôi chọn **Hybrid RRF + 2.400 ký tự** vì trên DEV, CER đạt **15/15**, cao hơn baseline **9/15** trong lần chạy Agent. Số câu trả lời đầy đủ tăng từ **6/15 lên 9/15**. Tôi khóa cấu hình trước khi chạy TEST và không chỉnh lại theo kết quả TEST. Vì tôi thay đổi cả phương pháp tìm kiếm và context budget, kết quả Agent không tách riêng được tác động của từng yếu tố.

Bằng chứng: `report/individual/checkpoint3a/metrics.json` và `report/individual/final-evaluation/`.

## 3. Agent và đánh giá

Tôi dùng mô hình **`gpt-4.1-mini`** với hai tool:

- `search`: tìm tối đa 3 chunk mỗi lần; Agent được tìm nhiều nhất 3 lần.
- `finish`: trả lời hoặc từ chối, kèm các `chunk_id` mà mô hình chọn làm nguồn.

Context giữ `chunk_id`, nguồn và số trang. Tôi giới hạn độ dài context ở 800 hoặc 2.400 ký tự tùy cấu hình. Bộ kiểm tra chỉ chấp nhận citation có trong context và kiểm tra nội dung được dẫn. Nếu thiếu bằng chứng hoặc không qua kiểm tra, Agent có thể từ chối. Các lần từ chối nhầm vẫn được tính là lỗi, không sửa kết quả khi chấm.

Tôi chạy **17 câu DEV** cho mỗi cấu hình, chốt cấu hình, rồi chạy **7 câu TEST** cho mỗi cấu hình đúng một lượt. Các trace cũ trong giai đoạn thử nghiệm không được trộn vào kết quả cuối.

### Kết quả Agent

| Cấu hình / split | Tool use | Số câu dùng 1/2/3 lần search | Grounded answer 0/1/2; TB /2 | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| Baseline / DEV | 17/17 (100%) | 10/2/5 | 9/0/6; **0,80** | 6/7 (85,7%) | 7/7 | 1/2 | 9/15 |
| Selected / DEV | 17/17 (100%) | 15/1/1 | 6/0/9; **1,20** | 10/10 (100%) | 9/9 | 2/2 | 6/15 |
| Baseline / TEST | 7/7 (100%) | 2/0/5 | 4/0/1; **0,40** | 1/1 (100%) | 1/1 | 2/2 | 4/5 |
| Selected / TEST | 7/7 (100%) | 4/0/3 | 3/0/2; **0,80** | 2/2 (100%) | 2/2 | 2/2 | 3/5 |

*Grounded answer: 0 = sai, thiếu hoặc từ chối; 1 = đúng một phần; 2 = đúng đầy đủ. Citation hợp lệ được tính theo số ID nguồn duy nhất, không phải số câu trả lời. Nhãn chấm được đối chiếu từ output và bằng chứng, chưa phải đánh giá độc lập của giảng viên.*

### Một số câu tiêu biểu

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| q01 (DEV selected) | Có bằng chứng | `search` tìm được chunk phù hợp | Trả lời đúng, có nguồn trong context | **2 điểm**, citation hợp lệ |
| q05 (DEV selected) | Có bằng chứng | Hybrid giữ được điều kiện `30 mg/10 m` | Trả lời đủ điều kiện | **2 điểm**; cải thiện so với baseline |
| q12 (DEV selected) | Cần 2 nhóm bằng chứng | Tìm được cả Mode 1 và Mode 2 | Mô hình tạo nội dung và chọn nguồn đúng, nhưng validator từ chối | **0 điểm** vì câu trả lời cuối là từ chối |
| Câu về R32 (DEV selected) | Thiếu bằng chứng | Tìm thêm nhưng không có nguồn chứng minh áp dụng cho R32 | Từ chối trả lời | **Đúng**, tránh dùng nhầm thông tin R410A |
| t05 (TEST selected) | Có bằng chứng | Context có điều kiện cần thiết | Chuỗi `[2-49]` trong nội dung bị hiểu nhầm là citation, Agent từ chối | **0 điểm**; lỗi kiểm tra định dạng |

Tôi giữ nguyên trace và điểm của các câu bị từ chối, kể cả khi context đã có bằng chứng. Ví dụ `q12`, `q11` và `t05` cho thấy bộ kiểm tra citation/grounding còn quá chặt. Tôi không sửa validator sau khi xem TEST.

### Thời gian và chi phí

| Cấu hình / split | API requests | Input tokens | Output tokens | Tổng thời gian provider | Chi phí ước tính |
|---|---:|---:|---:|---:|---:|
| Baseline / DEV | 46 | 36.260 | 2.072 | 57,537 giây | $0,0178192 |
| Selected / DEV | 37 | 36.164 | 2.563 | 61,326 giây | $0,0185664 |
| Baseline / TEST | 24 | 19.174 | 884 | 26,525 giây | $0,0090840 |
| Selected / TEST | 20 | 21.846 | 1.052 | 26,726 giây | $0,0104216 |
| **Tổng** | **127** | **113.444** | **6.571** | **172,114 giây** | **$0,0558912** |

Tổng thời gian chạy cả hai giai đoạn DEV và TEST, gồm phần chuẩn bị trong runner, là **220,386 giây**. Không có lỗi API hoặc retry trong đợt đánh giá cuối. Chi phí là số ước tính theo đơn giá API, không phải hóa đơn thực tế; không tính các lần thử trước đó.

**Kết luận:** Hybrid RRF và context dài hơn giúp Agent tìm đủ bằng chứng tốt hơn. Trên TEST, CER đạt **5/5** nhưng chỉ có **2/5** câu được trả lời đầy đủ. Hạn chế chính là bộ kiểm tra đôi khi từ chối cả câu có bằng chứng đúng. Tôi thấy cần cải thiện phần này nếu dùng hệ thống thực tế, nhưng không thay đổi sau TEST để giữ kết quả đánh giá trung thực.

Trace, nhãn và cách chạy lại: `report/individual/final-evaluation/REPRODUCE.md`, cùng các thư mục `dev/`, `test/` bên trong `final-evaluation/`. Bộ kiểm thử offline đạt **83/83 PASS**.

## 4. Thử thách nâng cao (nếu thực hiện)

Tôi **không thực hiện** thử thách nâng cao với tài liệu 100 trang. Tôi tập trung hoàn thành phần cơ bản và đánh giá đúng trên bộ dữ liệu đã chọn.

## 5. Khả năng tái lập và lưu ý khi nộp

- Code chính: `src/retrievers.py`, `src/openai_agent.py`, `src/run_agent_suite.py`, `src/evaluate_agent_suite.py`.
- Benchmark và dữ liệu: thư mục `data/`.
- Kết quả và trace: `report/individual/checkpoint3a/` và `report/individual/final-evaluation/`.
- Hướng dẫn chạy lại: `report/individual/final-evaluation/REPRODUCE.md`.
- Môi trường: Python 3.13.7, PostgreSQL/pgvector và các thư viện trong `src/requirements.txt`.
- Cấu hình đã được khóa trước TEST; các file hash và dữ liệu Day 06 được kiểm tra không thay đổi.
