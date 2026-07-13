<script setup lang="ts">
import { toGoalStats, type Goal } from "../models/goal";
import { useSession } from "../stores/session";
import { formatDec } from "../utils";

const props = defineProps<{
    goal: Goal;
}>();

const session = useSession();
const stats = toGoalStats(props.goal, session.settings!.distance_unit);

const progress = stats.goal.current_distance_meters / stats.goal.distance_meters * 100;
</script>

<template>
    <div class="col-lg-6">
        <div class="card bg-body-tertiary border-0">
            <div class="card-body">
                <div class="card-title">{{ stats.name }}</div>
                <div class="card-text">
                    {{ formatDec(stats.total_dist, 2) }} {{ stats.dist_abbr }} in {{ stats.total_days }} days
                    <br />
                    <div class="progress my-2" role="progressbar" aria-label="Goal progress"
                        :aria-valuenow="stats.goal.current_distance_meters" aria-valuemin="0"
                        :aria-valuemax="stats.goal.distance_meters">
                        <div class="progress-bar progress-bar-striped" :style="{ width: `${progress}%` }">
                        </div>
                    </div>

                    {{ formatDec(stats.current_dist, 2) }} {{ stats.dist_abbr }} / {{ formatDec(stats.percent, 0) }}%
                    complete
                    ({{ formatDec(Math.abs(stats.current_pace_diff), 2) }}
                    {{ stats.current_pace_diff >= 0 ? "over" : "under" }} pace)<br />
                    {{ stats.remaining_days }} days to go ({{ formatDec(stats.remaining_pace, 2) }} {{ stats.dist_abbr
                    }}
                    per
                    day)
                </div>
            </div>
        </div>
    </div>
</template>
