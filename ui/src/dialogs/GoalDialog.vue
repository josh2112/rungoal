<script setup lang="ts">
import { Temporal } from "temporal-polyfill";
import { computed, onMounted, ref } from "vue";
import { useDialog } from "../composables/dialog.ts";
import type { Goal, GoalCreate, GoalUpdate } from "../models/goal.ts";
import { useSession } from "../stores/session.ts";
import { currentLocale, distanceAbbr, distanceConvert, formatDec } from "../utils.ts";

const props = defineProps<{
    goal: Goal | undefined;
}>();

const today = Temporal.Now.plainDateISO();

const goal = ref<Goal | GoalCreate>({
    start_date: today,
    end_date: today,
    distance_meters: 1,
} as GoalCreate);

// GoalCreate doesn't have id
const isUpdate = computed(() => "id" in goal.value);

const session = useSession();

const dialogRef = ref<Element>();
const { open, close } = useDialog(dialogRef);
defineExpose({ open })


onMounted(() => {
    if (props.goal) {
        goal.value = props.goal;
    } else {
        distance.value = 10;
        spanType.value = "month";
        onRadioChanged();
    }
});

const submit = () => {
    close();
    if (isUpdate.value) {
        session.updateGoal(goal.value as GoalUpdate);
    } else {
        session.addGoal(goal.value);
    }
};

const startDate = computed({
    get() {
        return goal.value.start_date.toString();
    },
    set(value) {
        goal.value.start_date = Temporal.PlainDate.from(value);
        onRadioChanged();
    },
});

const endDate = computed({
    get() {
        return goal.value.end_date.toString();
    },
    set(value) {
        goal.value.end_date = Temporal.PlainDate.from(value);
        onRadioChanged();
    },
});

const distance = computed({
    get() {
        return distanceConvert(goal.value.distance_meters, "meters", session.settings.distance_unit);
    },
    set(value) {
        goal.value.distance_meters = distanceConvert(value, session.settings.distance_unit, "meters");
    },
});

const durationDays = computed(() => goal.value.start_date.until(goal.value.end_date).days + 1);

const spanType = ref<"year" | "month" | "custom">("custom");

const formatDuration = (length: number, name: string) => length ? `${length} ${name}${length == 1 ? "" : "s"}` : "";

const formatGoalTitle = () => {
    let start = `${goal.value.start_date.toLocaleString(currentLocale, { dateStyle: "long" })}: `;
    const diff = goal.value.start_date.until(goal.value.end_date.add({ days: 1 })).round({
        largestUnit: "year",
        relativeTo: goal.value.start_date
    });

    const years = formatDuration(diff.years, "year"), months = formatDuration(diff.months, "month"),
        weeks = formatDuration(diff.days / 7, "week"), days = formatDuration(diff.days, "days");

    const durations = [years, months, weeks, days].filter((v) => v).join(' ')

    return `${start} ${durations}`;
};

const onRadioChanged = () => {
    const today = Temporal.Now.plainDateISO();

    switch (spanType.value) {
        case "year":
            goal.value.start_date = today.with({ month: 1, day: 1 });
            goal.value.end_date = today.with({ month: 12, day: 31 });
            console.log(goal.value.start_date);
            goal.value.name = `Year of ${goal.value.start_date.year}`;
            break;
        case "month":
            goal.value.start_date = today.with({ day: 1 });
            goal.value.end_date = today.with({ day: today.daysInMonth });
            goal.value.name = `${goal.value.start_date.toLocaleString(currentLocale, { month: "long" })} ${goal.value.start_date.year}`;
            break;
        case "custom":
            goal.value.name = formatGoalTitle();
    }
};
</script>

<template>
    <div ref="dialogRef" class="modal fade" tabindex="-1" aria-labelledby="goalModalTitle" aria-hidden="true">
        <div class="modal-dialog">
            <form @submit.prevent="submit">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="goalModalTitle">{{ isUpdate ? "Update" : "Add" }} Goal</h1>
                        <button type="button" class="btn-close" @click="() => close()" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="form-floating">
                            <input type="text" class="form-control" id="name" placeholder="_" required
                                v-model.number="goal.name" />
                            <label for="name">Name</label>
                        </div>

                        <div class="form-floating mt-3 input-group">
                            <input type="number" class="form-control" id="distance" placeholder="_" min="1" max="10000"
                                required v-model.number="distance" />
                            <label for="distance">Distance ({{ distanceAbbr(session.settings.distance_unit)
                            }})</label>
                            <span class="input-group-text">{{ formatDec(Math.max(0, distanceConvert(goal.distance_meters
                                / durationDays, "meters",
                                session.settings.distance_unit)), 2)
                            }} {{ distanceAbbr(session.settings.distance_unit) }}/day</span>
                        </div>

                        <div class="btn-group my-3 d-flex justify-content-center" role="group"
                            aria-label="Basic radio toggle button group">
                            <input type="radio" class="btn-check" name="radioGroup" id="year" autocomplete="off"
                                value="year" v-model="spanType" @change="onRadioChanged">
                            <label class="btn btn-outline-primary" for="year">This year</label>

                            <input type="radio" class="btn-check" name="radioGroup" id="month" autocomplete="off"
                                value="month" v-model="spanType" @change="onRadioChanged">
                            <label class="btn btn-outline-primary" for="month">This month</label>

                            <input type="radio" class="btn-check" name="radioGroup" id="custom" autocomplete="off"
                                value="custom" v-model="spanType" @change="onRadioChanged">
                            <label class="btn btn-outline-primary" for="custom">Custom</label>
                        </div>

                        <fieldset :disabled="spanType != 'custom'">
                            <div class="form-floating">
                                <input type="date" class="form-control" id="startDate" placeholder="_" min="2000-01-01"
                                    max="2100-12-31" v-model="startDate" required />
                                <label for="startDate">Start date</label>
                            </div>
                            <div class="form-floating mt-3">
                                <input type="date" class="form-control" id="endDate" placeholder="_" min="2000-01-01"
                                    max="2100-12-31" v-model="endDate" required />
                                <label for="endDate">End date (inclusive)</label>
                            </div>
                        </fieldset>
                    </div>
                    <div class="modal-footer">
                        <button type="submit" class="btn btn-primary">{{ isUpdate ? "Update" : "Add" }}</button>
                    </div>
                </div>
            </form>
        </div>
    </div>
</template>
