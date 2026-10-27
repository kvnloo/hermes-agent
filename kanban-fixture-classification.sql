-- Read-only incident classification. Safe command:
-- sqlite3 -readonly /path/to/kanban.db < kanban-fixture-classification.sql
SELECT
  CASE
    WHEN tenant = 'bench' THEN 'scale-benchmark'
    WHEN created_by = 'desktop-e2e' THEN 'desktop-e2e'
    WHEN created_by = 'preview-fixture' THEN 'preview-fixture'
    ELSE 'long-card-fixture'
  END AS fixture_class,
  count(*) AS fixture_rows,
  min(created_at) AS first_created_at,
  max(created_at) AS last_created_at
FROM tasks
WHERE (tenant = 'bench' AND title GLOB 'bench [0-9]*'
       AND substr(title, 7) NOT GLOB '*[^0-9]*')
   OR (created_by IN ('desktop-e2e', 'preview-fixture') AND title LIKE 'Synthetic %')
   OR (created_at = 1787030032 AND created_by IS NULL AND tenant IS NULL
       AND title GLOB 'Long card [0-7] detail*')
GROUP BY fixture_class
ORDER BY fixture_rows DESC;