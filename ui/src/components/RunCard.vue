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
                <div class="d-flex justify-content-between card-title">
                    <h5 class="text-primary-emphasis">{{ stats.date_str }}</h5>
                    <h5 class="text-end">{{ formatDec(stats.distance, 2) }} {{ stats.dist_abbr }}</h5>
                </div>
                <div class="d-flex justify-content-between card-text">
                    <div>
                        <div v-if="stats.run.calories">{{ stats.run.calories }} cal</div>

                    </div>
                    <div class="text-end">
                        <div>{{ stats.duration_str }}</div>
                        <div>{{ stats.pace_str }} min/{{ stats.dist_abbr }}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
