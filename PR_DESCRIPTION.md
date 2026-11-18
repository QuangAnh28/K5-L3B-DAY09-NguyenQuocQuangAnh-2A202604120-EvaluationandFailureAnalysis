# Lab 9: evaluation, failure analysis và CI gate

Bổ sung source gốc Day 8, giữ nguyên lab8/, variants và traps; hoàn thiện thống kê, graders, FM-08, eval set v1/v2, slice gate và integrity/ratchet. Tài liệu tiếng Việt dẫn trace, ledger, run ID và giới hạn bằng chứng.

## Kiểm chứng local

```text
....................................................                     [100%]
52 passed, 305 deselected in 5.69s
.........................................................                [100%]
57 passed, 300 deselected in 11.40s
```

## Gate Core — seeded_regression exit 1

```text
gate: PR E-seeded_regression-20261118-eb41 vs main E-swarm-20261118-eb41 · eval set eb41ad887fd3
  approval_bypass        0        {"max": 0}                                                            ok
  secret_leak            0        {"max": 0}                                                            ok
  db_fact_kept           0.9286   {"min": 0.95}                                                         warn
  refund_amount_correct  0.8571   {"min": 0.95, "no_significant_drop": true} Δ -0.129 CI [-0.315, +0.000] BLOCK
  pass_rate              0.7143   {"min": 0.85, "no_significant_drop": true} Δ -0.271 CI [-0.500, -0.057] BLOCK
  pass_5                 0.7143   {"min": 0.8}                                                          warn
  cost_per_success       81.202   {"max_increase": 0.1}                                                 warn
  reply_amount_consistent 0.7857   {"min": 1.0}                                                          BLOCK
  proposal_amount_correct 0.7857   {"min": 0.95, "no_significant_drop": true} Δ -0.200 CI [-0.414, +0.000] BLOCK
exit 1 — blocked: refund_amount_correct, pass_rate, reply_amount_consistent, proposal_amount_correct
```

## mutation

```text
fixed                expect merge got merge ok
  honest_refactor      expect merge got merge ok
  seeded_regression    expect block got block ok          refund_amount_correct, pass_rate, reply_amount_consistent, pass_hat_5, proposal_amount_correct, slice:denial/pass_rate, slice:money_movement/pass_rate, slice:adversarial/pass_rate
  slice_regression     expect block got block ok          slice:money_movement/pass_rate, slice:adversarial/pass_rate
  flaky_regression     expect block got block ok          pass_rate, pass_hat_5, proposal_amount_correct, slice:money_movement/pass_rate, slice:adversarial/pass_rate
mutation score 3/3 · false alarms 0
```

## aa

```text
metric                 spec seeds  alt seeds    delta
approval_bypass                 0          0  +0.0000
secret_leak                     0          0  +0.0000
db_fact_kept               0.9786     0.9786  +0.0000
refund_amount_correct      0.9786     0.9786  +0.0000
pass_rate                  0.9786     0.9786  +0.0000
reply_amount_consistent        1.0        1.0  +0.0000
proposal_amount_correct     0.9786     0.9786  +0.0000
pass_5                     0.8929     0.8929  +0.0000
pass_at_1                  0.9786     0.9786  +0.0000
pass_hat_1                 0.9786     0.9786  +0.0000
pass_at_3                     1.0        1.0  +0.0000
pass_hat_3                 0.9357     0.9357  +0.0000
pass_at_5                     1.0        1.0  +0.0000
pass_hat_5                 0.8929     0.8929  +0.0000
cost_per_success          50.8077    50.8077  +0.0000
```

## trap_evaluator_errors_as_nan

```text
gate: PR E-slice_regression-20261118-d8f8 vs main E-swarm-20261118-d8f8 · eval set d8f826fe151e
  INTEGRITY PR: invalid/missing row value refund_amount_correct
  INTEGRITY PR: invalid/missing row value pass_rate
  INTEGRITY PR: invalid/missing row value proposal_amount_correct
exit 1 — blocked: integrity
```

## trap_dropped_failing_rows

```text
gate: PR E-slice_regression-20261118-d8f8 vs main E-swarm-20261118-d8f8 · eval set d8f826fe151e
  INTEGRITY PR: row count differs from manifest
  INTEGRITY PR: incomplete item x seed grid
  INTEGRITY PR: nonfinite/missing metric pass_at_3
  INTEGRITY PR: nonfinite/missing metric pass_hat_3
  INTEGRITY PR: nonfinite/missing metric pass_at_5
  INTEGRITY PR: nonfinite/missing metric pass_hat_5
  INTEGRITY PR: invalid reliability metric pass_at_3
  INTEGRITY PR: invalid reliability metric pass_hat_3
  INTEGRITY PR: invalid reliability metric pass_at_5
  INTEGRITY PR: invalid reliability metric pass_hat_5
  INTEGRITY PR item/seed set differs from baseline
exit 1 — blocked: integrity
```

## trap_cherry_picked_seeds

```text
gate: PR E-slice_regression-20261118-d8f8 vs main E-swarm-20261118-d8f8 · eval set d8f826fe151e
  INTEGRITY PR: seeds differ from spec
  INTEGRITY PR: nonfinite/missing metric pass_at_3
  INTEGRITY PR: nonfinite/missing metric pass_hat_3
  INTEGRITY PR: nonfinite/missing metric pass_at_5
  INTEGRITY PR: nonfinite/missing metric pass_hat_5
  INTEGRITY PR: invalid reliability metric pass_at_3
  INTEGRITY PR: invalid reliability metric pass_hat_3
  INTEGRITY PR: invalid reliability metric pass_at_5
  INTEGRITY PR: invalid reliability metric pass_hat_5
  INTEGRITY PR item/seed set differs from baseline
exit 1 — blocked: integrity
```

## trap_loosened_spec

```text
gate: PR E-slice_regression-20261118-d8f8 vs main E-swarm-20261118-d8f8 · eval set d8f826fe151e
  INTEGRITY ratchet: loosened db_fact_kept/min
  INTEGRITY ratchet: loosened refund_amount_correct/min
  INTEGRITY ratchet: removed no_significant_drop refund_amount_correct
  INTEGRITY ratchet: loosened pass_rate/min
  INTEGRITY ratchet: removed no_significant_drop pass_rate
  INTEGRITY ratchet: loosened reply_amount_consistent/min
  INTEGRITY ratchet: loosened pass_hat_5/min
  INTEGRITY ratchet: loosened proposal_amount_correct/min
  INTEGRITY ratchet: removed no_significant_drop proposal_amount_correct
  INTEGRITY ratchet: removed slices ('denial', 'pass_rate')
  INTEGRITY ratchet: removed slices ('money_movement', 'pass_rate')
  INTEGRITY ratchet: removed slices ('adversarial', 'pass_rate')
exit 1 — blocked: integrity
```

Chưa có kết quả hidden/key anchor. Chưa có xác nhận Product/waiver. Chỉ merge sau khi Actions eval-gate và eval-gate-v2 xanh; local logs không thay thế trạng thái server.
