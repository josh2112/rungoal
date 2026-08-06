<script setup lang="ts">
import { onMounted } from "vue";
import NotableRunCard from "../components/NotableRunCard.vue";
import { navbarState } from "../models/misc";
import type { Run, Weather } from "../models/run.ts";
import { useSession } from "../stores/session";
import { distanceAbbr, durationFormatter, formatDec, temperatureAbbr, temperatureConvert } from "../utils";

const session = useSession();

onMounted(() => {
    navbarState.title = "Notable runs";
    navbarState.actions = [];
});

const distAbbr = distanceAbbr(session.settings.distance_unit);

const tempStr = (wx?: Weather) => {
    const unit = session.settings.temperature_unit;
    const abbr = temperatureAbbr(unit);
    const temp = wx?.temp_c ? Math.round(temperatureConvert(wx.temp_c, "celsius", unit)) : undefined;
    const apparent_temp = wx?.apparent_temp_c
        ? Math.round(temperatureConvert(wx.apparent_temp_c, "celsius", unit))
        : undefined;

    if (temp) {
        if (apparent_temp) return `${temp}${abbr} (Felt like ${apparent_temp}${abbr})`;
        else return `${temp}${abbr}`;
    }
};

const avgEfficiencyFactor = (run?: Run) => {
    const eff = run?.split_stats.map((s) => s.efficiency).filter((x): x is number => x !== null) ?? [];
    return eff.reduce((sum, val) => sum + val, 0) / (eff.length > 0 ? eff.length : 1);
};
</script>

<template>
    <div class="container mt-3">
        <NotableRunCard :run="session.notableRuns?.runs.HOTTEST">
            <h5>
                <span style="color: goldenrod"><i class="bi bi-thermometer-sun"></i> Hottest: </span>
                {{ tempStr(session.notableRuns?.runs.HOTTEST?.weather) }}
            </h5>
        </NotableRunCard>
        <NotableRunCard :run="session.notableRuns?.runs.COLDEST">
            <h5>
                <span style="color: steelblue"><i class="bi bi-thermometer-snow"></i> Coldest: </span>
                {{ tempStr(session.notableRuns?.runs.COLDEST?.weather) }}
            </h5>
        </NotableRunCard>
        <NotableRunCard :run="session.notableRuns?.runs.WETTEST">
            <h5>
                <span style="color: #3366ff"><i class="bi bi-cloud-rain-heavy"></i> Wettest: </span>
                {{ session.notableRuns?.runs.WETTEST?.weather?.rain_mm }} mm/hour
            </h5>
        </NotableRunCard>
        <NotableRunCard :run="session.notableRuns?.runs.EARLIEST">
            <h5 style="color: orange"><i class="bi bi-sunrise"></i> Earliest</h5>
        </NotableRunCard>
        <NotableRunCard :run="session.notableRuns?.runs.LATEST">
            <h5 style="color: lightslategray"><i class="bi bi-moon-stars"></i> Latest</h5>
        </NotableRunCard>
        <NotableRunCard :run="session.notableRuns?.runs.FASTEST">
            <h5>
                <i class="bi bi-lightning"></i> Fastest:
                {{ durationFormatter(session.notableRuns!.runs.FASTEST!.average_pace) }} min/{{ distAbbr }}
            </h5>
        </NotableRunCard>
        <NotableRunCard :run="session.notableRuns?.runs.LONGEST">
            <h5>
                <i class="bi bi-signpost-split"></i> Longest:
                {{ formatDec(session.notableRuns!.runs.LONGEST!.distance, 2) }} {{ distAbbr }}
            </h5>
        </NotableRunCard>
        <NotableRunCard :run="session.notableRuns?.runs.MOST_EFFICIENT">
            <h5>
                <i class="bi bi-graph-up-arrow"></i> Most Efficient:
                {{ formatDec(avgEfficiencyFactor(session.notableRuns?.runs.MOST_EFFICIENT), 2) }} meters/heartbeat
            </h5>
        </NotableRunCard>
    </div>
</template>
