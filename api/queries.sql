-- database: rungoal.db
select
    goal.start_date,
    goal.end_date,
    coalesce(sum(run.distance_millimeters), 0) / 1609344.0
from
    goal
    left outer join run ON date(run.start_time) >= goal.start_date
    AND date(run.start_time) <= goal.end_date
WHERE
    goal.user_id = 1
group by
    goal.id
order by
    goal.start_date desc;

select run.start_time, round(run.distance_millimeters / 1609344.0, 2) as mi from run where user_id = 1 and start_time >='2026-01-01' order by start_time desc;