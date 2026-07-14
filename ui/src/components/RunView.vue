<script setup lang="ts">
import { computed } from "vue";
import { toRunStats, type Run } from "../models/run";
import { useSession } from "../stores/session";
import { formatDec } from "../utils";

const props = defineProps<{
    run: Run;
}>();

const session = useSession();

const stats = computed(() => toRunStats(props.run, session.settings!.distance_unit));
</script>

<template>
    <div class="col-lg-6">
        <div class="card bg-body-tertiary rounded-4 border-0">
            <div class="card-body">
                <div class="d-flex justify-content-between">
                    <div>
                        <h5>{{ stats.date_str }}</h5>
                        <div v-if="stats.run.calories">{{ stats.run.calories }} cal</div>
                    </div>
                    <div class="text-end">
                        <h5>{{ formatDec(stats.distance, 2) }} {{ stats.dist_abbr }}</h5>
                        <div>{{ stats.duration_str }}</div>
                        <div>{{ stats.pace_str }} {{ stats.dist_abbr }} / min</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
