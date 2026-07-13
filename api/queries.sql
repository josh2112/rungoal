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

select
    id
from
    run
where
    date(run.start_time) > '2026-07-01';
