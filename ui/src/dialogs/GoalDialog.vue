<script setup lang="ts">
import { Modal } from "bootstrap";
import { Temporal } from "temporal-polyfill";
import { computed, onMounted, ref, watch } from "vue";
import type { Goal, GoalCreate, GoalUpdate } from "../models/goal.ts";
import { useDialogs } from "../stores/dialogs.ts";
import { useSession } from "../stores/session.ts";
import { currentLocale, distanceAbbr, distanceConvert } from "../utils.ts";

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
const dialogs = useDialogs();

const dialogRef = ref<Element>();
let dialog: Modal | null = null;

onMounted(() => {
    dialog = new Modal(dialogRef.value!);
    if (props.goal) {
        goal.value = props.goal;
    } else {
        distance.value = 10;
        spanType.value = "month";
        onRadioChanged();
    }
});

watch(
    () => dialogs.isGoalDialogOpen,
    (isOpen) => {
        if (isOpen) dialog?.show();
        else dialog?.hide();
    },
);

const close = () => {
    (document.activeElement as HTMLElement)?.blur();
    dialogs.isGoalDialogOpen = false;
};

const submit = () => {
    close();
    if (isUpdate) {
        session.addGoal(goal.value);
    } else {
        session.updateGoal(goal.value as GoalUpdate);
    }
};

const startDate = computed({
    get() {
        return goal.value.start_date.toString();
    },
    set(value) {
        goal.value.start_date = Temporal.PlainDate.from(value);
    },
});

const endDate = computed({
    get() {
        return goal.value.end_date.toString();
    },
    set(value) {
        goal.value.end_date = Temporal.PlainDate.from(value);
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

const spanType = ref<"year" | "month" | "custom">("custom");

const formatGoalTitle = () => {
    let name = `${goal.value.start_date.toLocaleString(currentLocale, { dateStyle: "long" })}: `;
    const diff = goal.value.start_date.until(goal.value.end_date).round({ largestUnit: "years" });

    if (diff.years > 0 && diff.months == 0 && diff.days == 0) {
        name = `${name} ${diff.years} year${diff.years == 1 ? "" : "s"}`;
    } else if (diff.months > 0 && diff.days == 0) {
        name = `${name} ${diff.months} month${diff.months == 1 ? "" : "s"}`;
    } else if (!(diff.days % 7)) {
        name = `${name} ${diff.days / 7} week${diff.days / 7 == 1 ? "" : "s"}`;
    } else {
        name = `${name} ${diff.days} day${diff.days == 1 ? "" : "s"}`;
    }

    return name;
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
            goal.value.name = `Month of ${goal.value.start_date.toLocaleString(currentLocale, { month: "long" })}`;
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
                            <input
                                type="number"
                                class="form-control"
                                id="distance"
                                placeholder="_"
                                min="1"
                                max="10000"
                                required
                                v-model.number="distance"
                            />
                            <label for="distance">Distance ({{ distanceAbbr(session.settings.distance_unit) }})</label>
                        </div>

                        <div class="my-3">
                            <div class="form-check">
                                <input
                                    id="thisYear"
                                    type="radio"
                                    class="form-check-input"
                                    name="radioGroup"
                                    value="year"
                                    v-model="spanType"
                                    @change="onRadioChanged"
                                /><label class="form-check-label" for="thisYear">This year</label>
                            </div>
                            <div class="form-check">
                                <input
                                    id="thisMonth"
                                    type="radio"
                                    class="form-check-input"
                                    name="radioGroup"
                                    value="month"
                                    v-model="spanType"
                                    @change="onRadioChanged"
                                /><label class="form-check-label" for="thisMonth">This month</label>
                            </div>
                            <div class="form-check">
                                <input
                                    id="custom"
                                    type="radio"
                                    class="form-check-input"
                                    name="radioGroup"
                                    value="custom"
                                    v-model="spanType"
                                    @change="onRadioChanged"
                                /><label class="form-check-label" for="custom">Custom:</label>
                            </div>
                        </div>

                        <fieldset :disabled="spanType != 'custom'">
                            <div class="form-floating">
                                <input
                                    type="date"
                                    class="form-control"
                                    id="startDate"
                                    placeholder="_"
                                    min="2000-01-01"
                                    max="2100-12-31"
                                    v-model="startDate"
                                    required
                                />
                                <label for="startDate">Start date</label>
                            </div>
                            <div class="form-floating mt-3">
                                <input
                                    type="date"
                                    class="form-control"
                                    id="endDate"
                                    placeholder="_"
                                    min="2000-01-01"
                                    max="2100-12-31"
                                    v-model="endDate"
                                    required
                                />
                                <label for="endDate">End date</label>
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
