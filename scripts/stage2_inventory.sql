-- Stage 2 deterministic inventory query (committed executable record).
-- Run: bench --site <site> console < scripts/stage2_inventory.sql
-- (via scripts/record_stage2_inventory.py which adds hashes/envelope).
-- Merkle scheme: sha256(repr(rows)) over rows ordered by ALL FIVE columns;
-- partial ORDER BY is nondeterministic on ties and MUST NOT be used.

SELECT COALESCE(ct_app,'<untagged>') AS app, COUNT(*) AS total,
 SUM(translated_text = '' OR translated_text IS NULL) AS empty,
 SUM(translated_text <> '' AND translated_text <> source_text) AS populated_nontrivial,
 SUM(translated_text = source_text) AS source_equal,
 SUM(ct_review_status = 'Released') AS released,
 SUM(ct_review_status = 'Pending') AS pending,
 SUM(ct_review_status = 'Approved') AS approved_legacy,
 SUM(ct_review_status = 'Deprecated') AS deprecated,
 SUM(ct_review_status IS NULL OR ct_review_status NOT IN ('Released','Pending','Approved','Deprecated')) AS no_status
FROM `tabTranslation` WHERE language='ar' GROUP BY app;

SELECT source_text, COALESCE(context,''), COALESCE(ct_app,'<untagged>'),
 COALESCE(translated_text,''), COALESCE(ct_review_status,'')
FROM `tabTranslation` WHERE language='ar'
ORDER BY source_text, context, ct_app, translated_text, ct_review_status;
