<script setup lang="ts">
import { useDark } from "@vueuse/core";
import { computed } from "vue";
import { toGoalStats, type Goal } from "../models/goal";
import { useSession } from "../stores/session";
import { formatDec } from "../utils";

const props = defineProps<{
    goal: Goal;
}>();

const isDark = useDark();

const session = useSession();
const stats = computed(() => toGoalStats(props.goal, session.settings!.distance_unit));

const progress = computed(() => (stats.value.goal.current_distance_meters / stats.value.goal.distance_meters) * 100);
</script>

<template>
    <div class="col-lg-6">
        <div class="card rounded-4 border-0 hover-highlight" :class="isDark ? 'bg-body-tertiary' : 'bg-body-secondary'">
            <div class="card-body">
                <div class="d-flex justify-content-between card-title">
                    <h5>
                        <RouterLink
                            :to="`/goal/${session.goals.indexOf(goal) + 1}`"
                            class="stretched-link text-decoration-none text-primary-emphasis"
                            >{{ stats.goal.name }}
                        </RouterLink>
                    </h5>
                    <h5
                        class="text-end"
                        :class="stats.current_pace_diff >= 0 ? 'text-success-emphasis' : 'text-danger-emphasis'"
                    >
                        {{ stats.current_pace_diff >= 0 ? "+" : "-"
                        }}{{ formatDec(Math.abs(stats.current_pace_diff), 2) }}
                        {{ stats.dist_abbr }}
                    </h5>
                </div>
                <div class="card-text">
                    <div>{{ formatDec(stats.total_dist, 2) }} {{ stats.dist_abbr }} in {{ stats.total_days }} days</div>
                    <div
                        class="progress my-2"
                        role="progressbar"
                        aria-label="Goal progress"
                        :aria-valuenow="stats.goal.current_distance_meters"
                        aria-valuemin="0"
                        :aria-valuemax="stats.goal.distance_meters"
                    >
                        <div class="progress-bar" :style="{ width: `${progress}%` }"></div>
                    </div>
                    <div>
                        {{ formatDec(stats.current_dist, 2) }} {{ stats.dist_abbr }} /
                        {{ formatDec(stats.percent, 0) }}% complete<br />
                    </div>
                    <div>
                        {{ stats.remaining_days }} days to go ({{ formatDec(stats.remaining_pace, 2) }}
                        {{ stats.dist_abbr }} per day)
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
