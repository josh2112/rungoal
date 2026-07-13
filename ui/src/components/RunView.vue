<script setup lang="ts">
import { toRunStats, type Run } from "../models/run";
import { useSession } from "../stores/session";
import { formatDec } from "../utils";

const props = defineProps<{
    run: Run;
}>();

const session = useSession();

const stats = toRunStats(props.run, session.settings!.distance_unit);
</script>

<template>
    <div class="col-lg-6">
        <div class="card bg-body-tertiary border-0">
            <div class="card-body">
                <div class="card-title">{{ stats.date_str }}</div>
                <div class="card-text">
                    <span v-if="stats.run.calories">{{ stats.run.calories }} cal</span>
                    {{ formatDec(stats.distance, 2) }} {{ stats.dist_abbr }}<br />
                    {{ stats.duration_str }}<br />
                    {{ stats.pace_str }} {{ stats.dist_abbr }} / min
                </div>
            </div>
        </div>
    </div>
</template>
