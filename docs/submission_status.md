# Trạng thái bàn giao

- Source gốc Day 8 đã tích hợp; không sửa lab8/, public variants hay traps.
- Eval set v1/v2, labels riêng, taxonomy 9 FM và evidence 8 lỗi/1 đối chứng quyền.
- Tất cả 38 lệnh acceptance trong `reports/verification.json` đã trả exit đúng kỳ vọng (bao gồm exit 1 có chủ đích).
- Test regression chạy lại sau khi thêm quiet_override/misreport: xem tests_lab9.txt.
- Tái lập từ src: `python -m lab9.verify`, rồi `python -m lab9.write_docs`.
- Source hash và môi trường: reports/environment.json; code commit `40827f8adf4eb6f3f6df8cecccfb162c8ea7afe4`. Report/tài liệu được commit riêng sau code.
- Mô tả PR đã soạn tại PR_DESCRIPTION.md; nhánh làm bài starter/d09.
- Cần thao tác server: bật Actions của fork, push nhánh, mở PR vào main của chính fork, đợi hai job xanh, merge trước hạn LMS, nộp link fork.
- Chưa thể xác nhận hidden/anchor key, ngày hạn LMS hay chữ ký phê duyệt Product. Không tự điền các thông tin chưa có.
