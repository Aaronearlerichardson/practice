-- GIVEN: the slow query for problem 14. Don't edit.
SELECT l.lab_id, l.patient_id, l.collected_at, l.value,
       (SELECT round(avg(l2.value), 2)
        FROM labs l2
        WHERE l2.patient_id = l.patient_id AND l2.test_code = 'HBA1C') AS patient_avg
FROM labs l
WHERE l.site_id = 'S12'
  AND l.test_code = 'HBA1C'
  AND l.collected_at >= '2025-04-01' AND l.collected_at < '2025-05-01'
  AND l.value > (SELECT avg(l2.value)
                 FROM labs l2
                 WHERE l2.patient_id = l.patient_id AND l2.test_code = 'HBA1C');
