# Calibration ledger — memory-update

One row per published or decided record with `record_type:
memory-update`. The auto-promote threshold (DEC-RQ-001) is 95%
approve-unchanged over at least twenty rows.

## Rows

- `rec-2026-08-14-001` — reviewer: vignesh — first verdict: approve
  (unchanged) — verdict latency: 26m16s — created_at:
  2026-08-14T12:34:56Z — first decided_at: 2026-08-14T13:01:12Z

## Aggregates (current)

- Rows: 1
- Approve-unchanged rate: 100% (1/1)
- Edit rate: 0%
- Reject rate: 0%
- Median verdict latency: 26m16s
- Auto-promote eligible: no — calibration set needs at least 20 rows
  per DEC-RQ-001.

## Notes

A single row is the seed of the set, not the set itself. The
aggregates above are reported for shape (the future quarterly
calibration reading will compute them this way) but they carry no
statistical weight at n=1.
