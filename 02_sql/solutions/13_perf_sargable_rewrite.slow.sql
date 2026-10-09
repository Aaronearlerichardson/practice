-- GIVEN: the slow query for problem 13. Don't edit.
SELECT l.lab_id, l.patient_id, s.site_name, l.collected_at, l.value, l.unit
FROM labs l
JOIN sites s ON s.site_id = l.site_id
WHERE upper(l.test_code) = 'K'
  AND date_trunc('day', l.collected_at) BETWEEN '2025-03-01' AND '2025-03-07'
ORDER BY l.collected_at DESC;
