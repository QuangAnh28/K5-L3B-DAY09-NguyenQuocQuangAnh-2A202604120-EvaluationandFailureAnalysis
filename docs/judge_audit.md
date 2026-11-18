# Judge audit — replay, FAIL là lớp dương

Nguồn: `src/reports/judge_calibration.json`, sinh bằng `lab9.evidence`; stdout CLI ở `judge_tone.txt`, `judge_helpful.txt`.
Floors: κ≥0,6; precision≥0,8; recall≥0,7; κ không xác định phải FAIL.

| Tiêu chí | n | TP/FP/FN/TN | κ | Precision | Recall | Quyết định |
|---|---:|---|---:|---:|---:|---|
| tone | 100 | 24/4/6/66 | 0.757 | 0.857 | 0.8 | Đạt floors |
| helpful | 100 | 9/0/21/70 | 0.375 | 1.0 | 0.3 | Loại khỏi gate |

## Audit bất đồng dựa trên reply và note công khai

| Case | Human / judge | Ai đúng theo dữ liệu cung cấp? | Điều chỉnh rubric / hành động |
|---|---|---|---|
| H-008 | FAIL / PASS | Human: xưng em, nha quá suồng sã | Phân biệt thân thiện với xưng hô phù hợp khiếu nại |
| H-017 | FAIL / PASS | Human: xưng bạn với khách lớn tuổi, theo note | Nêu quy tắc xưng hô; khi không biết tuổi thì dùng anh/chị |
| H-029 | FAIL / PASS | Human: không cần nhắn thêm là ra lệnh | Không cho qua chỉ vì mở đầu Dạ, vui lòng |
| H-042 | PASS / FAIL | Human: ngắn nhưng đủ ý | Không bắt buộc câu xin lỗi ở mọi reply |
| H-051 | PASS / FAIL | Human: refund được phép theo note | Không phạt máy móc từ tiếng Anh được nghiệp vụ chấp nhận |
| H-081 | PASS / FAIL | Judge đúng theo note: người đọc nhầm ticket | Đưa vào hàng đợi sửa nhãn sau adjudication; giữ nguyên CSV gốc và calibration hiện tại |
| H-088 | PASS / FAIL | Human: lặp Dạ là lỗi gõ nhẹ | Tách lỗi gõ khỏi lỗi thái độ nghiêm trọng |
| HL-015 | FAIL / PASS | Human: reply 55.000 nhưng note ledger 40.000 | Không dùng lịch sự làm đại diện cho đúng nghiệp vụ; kiểm tiền bằng code |
| HL-020 | FAIL / PASS | Human: reply 90.000 nhưng note ledger 120.000 | Đưa ledger vào tiêu chí đúng tiền; dùng grader FM-08 |

Đây là phân tích từ dữ liệu replay được cấp, không phải một vòng gán nhãn mới có người dùng thật. Với H-081, dữ liệu không kèm ticket để thẩm định độc lập: kết luận dựa trên note công khai; không sửa CSV để làm đẹp điểm.

Tone đạt floors trên tập này; chỉ dùng cho tiêu chí văn phong. Helpful precision=1 nhưng bỏ sót 21/30 lỗi, recall=0,3 và κ=0,375 nên không đủ điều kiện gate.
Rogan–Gladen dùng sensitivity=recall và specificity=TN/(TN+FP); tỉ lệ lỗi tone quan sát 0,28 được hiệu chỉnh thành 0,30. Helpful quan sát 0,09, hiệu chỉnh 0,30. Không suy rộng tỉ lệ này thành production prevalence.
Chưa có nhãn held-out mới, chưa thử rubric đã sửa bằng một lần đánh giá mới; calibration báo cáo vẫn dùng nhãn nguyên bản.
