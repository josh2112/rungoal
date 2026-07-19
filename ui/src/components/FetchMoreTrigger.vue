<script setup lang="ts">
import { ref } from "vue";
import { useFetchMore } from "../fetch_more";
import { useSession } from "../stores/session";

const session = useSession();

const fetchMoreTrigger = ref<Element>();
const isLoading = ref(false);
const hasMore = ref(true);

useFetchMore(fetchMoreTrigger, async () => {
    if (isLoading.value || !hasMore.value) return;

    isLoading.value = true;
    hasMore.value = await session.getPreviousRuns();
    isLoading.value = false;
});
</script>

<template>
    <div class="text-center mt-5" style="min-height: 50px" ref="fetchMoreTrigger">
        <div v-if="isLoading" class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <hr v-else-if="!hasMore" />
    </div>
</template>
