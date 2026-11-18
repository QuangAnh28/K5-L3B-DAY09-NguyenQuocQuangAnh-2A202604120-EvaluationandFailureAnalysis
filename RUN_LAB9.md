# Chạy lại Lab 9

Bài làm của Nguyễn Quốc Quang Anh — 2A202604120, L3B. Source gốc Day 8 được tích hợp, không dùng ba shape do nhóm sửa. Quy trình đánh giá dùng swarm/variants do đề cung cấp.

## Môi trường

Python 3.11–3.13; lần kiểm chứng local dùng Python 3.13.13 trong `.venv` ở root.

```powershell
# Từ root dự án, khi đã có Python phù hợp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r src/requirements.txt -r src/requirements-lab9.txt
cd src
python -m lab9.evalset --build --check
python -m lab9.evalset --v2 --build
python -m lab9.verify
python -m lab9.final_checks
python -m lab9.write_docs
```

Nếu máy chỉ có Python ngoài dải phiên bản, dùng `uv venv --python 3.13 .venv` từ root rồi activate trước khi cài dependency. Không cần API key. `verify` chạy tuần tự vì agent ghi trace; có thể mất vài phút. Không chạy hai lần verify đồng thời.

`verify` coi exit 1 của judge_helpful, regression gate và từng trap là kết quả đúng kỳ vọng; nếu có lỗi ngoài kỳ vọng thì dừng. JSON `reports/verification.json` lưu command, exit kỳ vọng và exit thực tế; TXT lưu stdout/stderr. Không sửa tay report. Eval set được ghi LF cố định và có .gitattributes để SHA không đổi khi chuyển Windows/Linux.

## Đọc kết quả

- [Eval card](docs/eval_card.md): metric, CI, A/A, mutation, giới hạn.
- [Failure taxonomy](docs/failure_taxonomy.md): chín FM, bằng chứng event và năm anchor tự đối chiếu.
- [Trace case](docs/trace_case.md): bước sai đầu tiên C-002@11 và regression test.
- [Judge audit](docs/judge_audit.md): tone/helpful calibration và audit bất đồng.
- [PRD v1.1](docs/PRD_v1.1.md): cổng merge, trách nhiệm và trạng thái phê duyệt.
- [Trạng thái bàn giao](docs/submission_status.md).
- Bằng chứng sửa lỗi review: `src/reports/review_regressions.json` và `review_regressions.txt`, được sinh trong `lab9.verify`.

Có thể kiểm tra lại source Lab 8 byte-for-byte với ZIP đã cấp:

```powershell
# Chạy trong src; thay đường dẫn nếu ZIP nằm nơi khác
python -m lab9.final_checks --day8-zip "C:\Users\Think Pad\Downloads\K5-Day8-From-Workflows-to-Agents-main.zip"
```

## Nộp bài

Nhánh làm bài: `starter/d09`. Nội dung PR đã chuẩn bị ở [PR_DESCRIPTION.md](PR_DESCRIPTION.md).

```powershell
# Từ root: reports bị gitignore nên phải force-add
 git add -A
 git add -f src/reports
```

Commit và push nhánh, bật Actions của fork, mở PR vào main của **chính fork**, dán PR_DESCRIPTION.md, đợi eval-gate và eval-gate-v2 xanh rồi merge trước hạn LMS. Nộp link fork theo SUBMISSION.md.
Chưa có bằng chứng hidden/key anchor hoặc phê duyệt pilot. Các mục đó được ghi rõ, không tự khai đã hoàn tất.
