-- 01. Latest HbA1c per patient, keeping ties
-- Write your query below, then run: python tasks.py check-sql 01
with latest as (
    select * from (
        select *,
            rank() over (PARTITION by patient_id order by collected_at) as rn
        from labs
        where test_code = 'HBA1C'
    )
    where rn=1
)
select
    patient_id,
    lab_id,
    collected_at,
    value
from latest
