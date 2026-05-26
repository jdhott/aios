# Patch Notes — D1.6.1

- Fixed D1.6 smoke-test failure where anchor-term candidate remained `medium` confidence.
- Calibrated anchor-domain high-confidence threshold to `score >= 14`.
- Preserved broad-term suppression for weak one-word matches such as `bread`.
- Preserved read-only behavior: `writes=0` and `execution_authority_impact=none`.
