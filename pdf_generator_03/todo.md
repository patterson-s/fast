# PDF Generator Improvement To-Do List

## Layout & Structure Issues

- [ ] **Compact to one-page layout** - BLUF left, smaller graphs right
- [ ] **Remove duplicate BLUF header** in PDF
- [ ] **Prioritize content order**: BLUF → Time trend → Distribution → Covariates (first to cut)
- [ ] **Target 2 pages max** (single sheet, front/back)

## Visualization Improvements

- [x] **Remove military expenditure variables** from covariate graph (weak relationship to violence)
- [x] **Darken the all-months line** in temporal chart (currently too light)
- [ ] **Make graphs smaller** to fit compact layout

## BLUF Content Issues

- [ ] **Fix "significant increase" language** for tiny forecasts (0.0-0.1 fatalities vs 0.0 historical)
- [x] **Remove same-month historical comparisons** (not in Patrick's model)
- [x] **Switch to regional percentiles** (Africa & Middle East only) instead of global
- [ ] **Add bold/color highlighting** for key numbers and comparisons
- [ ] **Explain what drives small increases** - more substantive interpretability
- [x] **Remove/downplay military expenditure** in BLUF text

## Data Processing Changes

- [x] **Filter comparisons to Africa & Middle East regions** using inafr/inme variables
- [ ] **Revise trend calculation logic** to avoid misleading "significant" language for negligible changes