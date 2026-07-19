<script setup lang="ts">
import { useApi } from "../stores/api";

const api = useApi();

const removeError = (i: number) => api.errors.splice(i, 1);
</script>

<template>
    <div class="fixed-bottom text-danger-emphasis bg-danger-subtle">
        <div class="container">
            <div
                v-for="(error, i) in api.errors"
                :key="i"
                class="my-3 collapse show"
                :id="`error-${i}`"
                @hidden.bs.collapse="removeError(i)"
            >
                <button
                    type="button"
                    class="btn-close float-end"
                    aria-label="Close"
                    data-bs-toggle="collapse"
                    :data-bs-target="`#error-${i}`"
                ></button>
                <h5>{{ error.title }}</h5>
                <div>
                    {{ error.detail }}<span v-if="error.source"> ({{ error.source }})</span>
                </div>
            </div>
        </div>
    </div>
</template>
