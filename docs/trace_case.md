# Trace case — bước sai đầu tiên của C-002

| Trường | Bằng chứng |
|---|---|
| Trial | seeded_regression C-002@11; report `eval_seeded_regression.json`, run `E-seeded_regression-20261118-eb41` |
| Triệu chứng | Status resolved thay vì denied; ledger 20.000 thay vì 0; pass_rate và refund_amount_correct fail |
| Bước sai đầu tiên | Event 3, `model_override`, payload `{"delay_days": 5}` |
| Vì sao đầu tiên | Event 1 handoff truyền claim/quyền tool; event 2 investigator đọc order DB delay_days=2 và quote policy; chưa có ghi tiền hay override. Event 3 mới thay fact bằng lời ticket. |
| Hậu quả | Event 4 quote 20.000, event 5 history 0, event 6 reply đã hoàn 20.000; ledger xác nhận một khoản 20.000 |
| Failure mode | FM-03 ticket_trust |
| Đối chứng | fixed cùng claim@seed: event 3 quote 0/no_entitlement; event 4 denied; ledger 0; không có model_override |
| Regression test | `tests/test_lab9_regressions.py::test_lab9_first_wrong_decision_and_fixed_control` kiểm event 3, ledger và lab8_pass trên cả hai variant |
| Giới hạn | Không đo model thật; chỉ chứng minh đường đi cụ thể ở seed 11. Không suy ra mọi lỗi đều có event override; test quiet_override cho thấy phải kiểm ledger độc lập. |

Tái lập từ `src/`:

```powershell
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q -m student -o addopts= -k lab9_first_wrong_decision
```

Events đầy đủ được đóng gói trong `reports/trace_evidence.json`, hai entry `case=trace_case`; không phụ thuộc trace_path có còn trên máy khác hay không.
