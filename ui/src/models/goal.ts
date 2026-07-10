import { Temporal } from "temporal-polyfill";
import { currentLocale, distanceAbbr, distanceConvert, type DistanceUnit } from "../utils";


interface GoalDTO {
    id: number;
    distance_meters: number;
    start_date: string;
    end_date: string;
    current_distance_meters: number;
}

export interface Goal extends Omit<GoalDTO, "start_date" | "end_date"> {
    start_date: Temporal.PlainDate;
    end_date: Temporal.PlainDate;
}

export interface GoalStats {
    goal: Goal;
    dist_abbr: string;
    name: string;
    total_dist: number;
    current_dist: number;
    remaining_dist: number;
    total_days: number;
    elapsed_days: number;
    remaining_days: number;
    remaining_pace: number;
    current_pace_diff: number;
    percent: number;
}

export const toGoal = (dto: GoalDTO): Goal => ({
    ...dto,
    start_date: Temporal.PlainDate.from(dto.start_date),
    end_date: Temporal.PlainDate.from(dto.end_date)
})


export function toGoalStats(goal: Goal, distUnit: DistanceUnit): GoalStats {
    const today = Temporal.Now.plainDateISO();
    const daysTotal = goal.start_date.until(goal.end_date).days + 1;
    const daysRemaining = today.until(goal.end_date).days;

    const distance = (v: number) => distanceConvert(v, "meters", distUnit);

    return {
        goal: goal,
        dist_abbr: distanceAbbr(distUnit),
        name: goal.start_date.toLocaleString(currentLocale, { dateStyle: "full" }),

        total_dist: distance(goal.distance_meters),
        current_dist: distance(goal.current_distance_meters),
        remaining_dist: distance(goal.distance_meters - goal.current_distance_meters),

        total_days: daysTotal,
        elapsed_days: goal.start_date.until(today).days + 1,
        remaining_days: daysRemaining,

        remaining_pace: distance((goal.distance_meters - goal.current_distance_meters) / daysRemaining),

        current_pace_diff: distance(goal.current_distance_meters - (1 - daysRemaining / daysTotal) * goal.distance_meters),

        percent: goal.current_distance_meters / goal.distance_meters * 100
    } as GoalStats;
}

