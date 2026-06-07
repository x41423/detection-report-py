# Code Review Report — Key Findings

> Source: docs/code-review-report.html (2026-06-07)
> Sanitized for wiki ingestion

## Summary

142 Python files + 110 Vue/TS files reviewed.
12 issues found: 3 high-risk, 5 medium-risk, 4 suggestions.

## High Risk Issues
1. Database dual-write out of sync (SQLite vs MySQL field mismatches) → resolved by removing SQLite
2. Sensitive files in git history (mcporter.json, _tok.txt, =7.0.0, mcp_commands.txt) → deleted
3. Transaction summary LIKE matching (product_name LIKE '%supplier%') → changed to exact merchant_name match

## Medium Risk Issues
4. Frontend API errors silently swallowed (empty catch blocks) → fixed across 16 pages
5. Bare except clauses in migration.py + PyQt5 views → fixed to except Exception
6. Response format inconsistency (agreement_price.py) → added message field
7. UPDATE dynamic field concatenation (supplier_repository.py) → added whitelist
8. Missing Service layer (agreement_price.py) → assessed as unnecessary (pure CRUD)

## Suggestions
9. Token in localStorage → verified using httpOnly cookie (already secure)
10. Large file splitting (store.py 2028 lines, OrderManagement.vue 937 lines) → Phase 2 planned
11. Missing audit logging for CRUD operations → Phase 2 planned
12. Missing 404 catch-all route → added NotFound.vue

## Phase 2 Tasks
- store.py split by domain (schema/_orders.py, _products.py, _purchase.py, _pricing.py, _other.py)
- OrderManagement.vue search composable extraction
- Audit logging in Route layer for key operations
