-- 11. Median and percentiles per test
-- Write your query below, then run: python tasks.py check-sql 11
with latest as (
   select *
   from (
      select *, row_number() over (partition by site_id, source_record_id
                                   order by loaded_at desc, lab_id desc) as rn
      from labs
   )
   where rn = 1
),
filtered as (
   select *
   from latest
   where case 
      when test_code = 'GLU' then lower(unit) = 'mg/dl'
      when test_code = 'CREAT' then lower(unit) = 'mg/dl'
      when test_code = 'HGB' then lower(unit) = 'g/dl'
      when test_code = 'K' then lower(unit) = 'mmol/l'
      when test_code = 'NA' then lower(unit) = 'mmol/l'
      when test_code = 'ALT' then lower(unit) = 'u/l'
      when test_code = 'HBA1C' then lower(unit) = '%'
      when test_code = 'PLT' then lower(unit) = '10*3/ul'
      end
      AND value is not null
)
select
   test_code,
   count(distinct (site_id, source_record_id)) as n,
   percentile_disc(.1) within group (order by value) as p10,
   percentile_cont(.5) within group (order by value) as median,
   percentile_disc(.9) within group (order by value) as p90,
   round(avg(value), 2) as mean
from filtered
group by 1;
-- having loaded_at = max(loaded_at) over lab_id
--  group by 1, 2
-- order by 8
