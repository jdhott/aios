# Patch Notes — D1.6 Strong-Domain Confidence Calibration

## Changed

- Added anchor-domain term classification for specific operational terms.
- Confidence scoring now allows a single strong anchor term to reach high confidence when the historical neighborhood score is strong.
- Moved label/labels out of weak terms and into strong signal terms.
- Added telemetry line:
  - `Strong-domain confidence: anchor_terms_enabled=true; broad_terms_still_suppressed=true`

## Unchanged

- Read-only behavior.
- Database resolution behavior from D1.5.
- Project name resolution behavior.
- Active affinity preview remains observational only.
- No project relation writes.
- No execution ranking changes.
