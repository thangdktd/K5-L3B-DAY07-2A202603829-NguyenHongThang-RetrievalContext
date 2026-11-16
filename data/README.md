# Định dạng dữ liệu

Các file `example_*.json` chỉ minh họa định dạng, không đủ để nộp bài. Dữ liệu thật là JSON array UTF-8; nếu dùng định dạng khác, ghi cách chuyển trong README.

- **Chunk:** `id`, `text`, `source_id`, `source`, `page`, `metadata`. ID phải duy nhất; giữ phiên bản hoặc ngày nếu có.
- **Câu có đáp án:** `id`, `split` (`dev` hoặc `test`), `question`, `expected_answer`, `gold`: danh sách `{source_id, page, evidence}`. Với schema mẫu, mỗi evidence phải nằm trọn trong một chunk đúng nguồn và trang; các phần tử `gold` là evidence thay thế. Với câu multi-hop cần nhiều đoạn, bạn có thể mở rộng schema, ghi rõ nhóm evidence bắt buộc và cách chấm. Có thể thêm `filter` do người dùng cung cấp trước.
- **Câu thiếu evidence:** `id`, `split`, `question`, `answerable: false`, `expected_behavior: "search_and_abstain"`, `absence_reason`. Xem `agent_cases_example.json`.

Không đưa `gold` hoặc nhãn đáp án vào model và retrieval tool. Ghi nguồn dữ liệu và quyền sử dụng. Cách chuyển một số định dạng Day 6: [starter/README.md](../starter/README.md).

## Day 07 benchmark schema v2 and freeze

Official generator: `src/build_final_benchmark.py`. Inputs are the preserved
`data/questions_day6_raw.json` and the unchanged Day 06 strategy B chunk export
`data/chunks.json`; new TEST definitions remain in the generator. Legacy writers
are retired. No gold quote, question or expected answer was changed for q12:
its two existing quotes are represented as `gold_groups: [[mode1], [mode2]]`.

Required groups use AND; alternatives within a group use OR. Legacy `gold`
remains one OR group. Matching requires source_id, physical page and contiguous
NFC/whitespace-normalized quotation in a single chunk. Across chunks, evidence
is aggregated only through groups, never by joining text into a false quotation.

Hit@1 requires all groups in rank 1 alone; Evidence Hit@3 requires all groups in
the top 3 union; Context Evidence Rate requires all groups in the packed context.
All use answerable questions as denominator; also report single-group and
multi-group subsets separately. Thus q12 cannot pass strict Hit@1 with the current
split chunks. This implements the permitted multi-evidence extension in
BENCHMARK.md sections 1-2; it does not redefine partial evidence as complete.

Baseline uses top 3 and 800 characters including source headers. Comparison also
uses 2400 characters as a declared DEV context experiment. Full chunks are packed
in rank order with deduplication; chunks that do not fit are skipped. These are
retrieval/context proxies: no model is called or sent context during 3A.

Unanswerable review: scan all 292 chunks using the terms saved in
`unanswerable_audit.json`, inspect related extracted text and record scope/limits.
Keyword absence alone does not prove semantic absence; visual/extraction omissions
remain possible. No claims are made about contents of external service manuals.
TEST metadata/gold validation is an authorized annotation audit, not retrieval or
configuration tuning. No TEST queries are executed.

Build before freeze: `python -X utf8 src/build_final_benchmark.py`.
Freeze after tests/validation/DEV baseline: add `--freeze`.
After freeze, only `--check` is permitted: it rebuilds in memory, compares bytes,
and verifies SHA-256. `benchmark_manifest.json` records schema, date, counts,
scoring rules, input/generator/evaluator hashes. No benchmark modification is
permitted after freeze. To recreate chunks from Day 06, apply
`prepare_data.convert_chunk` to the original `chunks_B.jsonl`; the retired script
entry point never writes data. Rebuilding questions/cases requires no Day 06 write.
