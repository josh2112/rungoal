<script setup lang="ts">
import { ref, watch } from "vue";
import { useSession } from "../stores/session";

const session = useSession();

const img = ref<HTMLImageElement>();

watch(
    () => session.user,
    async () => {
        img.value!.src = await session.getTestTile(9043, 12963, 15);
    },
);
</script>

<template>
    <div class="text-center" style="background-color: beige">
        <img ref="img" />
    </div>
</template>
