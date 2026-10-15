SELECT *
-- c.name,
--  COUNT(v.visit_id)
FROM clinics c
LEFT JOIN visits v ON v.clinic_id = c.clinic_id
-- and v.status = 'completed' 
-- AND v.visit_date >= '2025-01-01' 
-- AND v.visit_date < '2026-01-01'
-- GROUP BY c.name;

-- select *
-- from visits v
-- WHERE v.status = 'completed' AND v.visit_date >= '2025-01-01' AND v.visit_date < '2026-01-01'