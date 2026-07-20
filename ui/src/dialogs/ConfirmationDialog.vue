<script setup lang="ts">
import { ref } from 'vue';
import { useDialog } from '../composables/dialog';

const props = defineProps<{
    params: DialogParams;
}>();


interface DialogButton {
    title: string;
    action: () => void;
    isCancel?: boolean;
    isPrimary?: boolean;
    isNegative?: boolean;
}

export interface DialogParams {
    title: string;
    message: string;
    isCancelable: boolean;
    buttons: DialogButton[];
}

const dialogRef = ref<Element>();
const { open, close } = useDialog(dialogRef);
defineExpose({ open })

const closeAndAction = (button: DialogButton) => {
    close();
    if (!button.isCancel)
        button.action();
}

const buttonClass = (button: DialogButton) => {
    if (button.isNegative) return 'btn-danger';
    else if (button.isPrimary || props.params.buttons.length == 1) return 'btn-primary';
    else return 'btn-secondary';
};
</script>

<template>
    <div ref="dialogRef" class="modal fade" tabindex="-1" aria-labelledby="dlgTitle" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h1 class="modal-title fs-5" id="dlgTitle">{{ props.params.title }}</h1>
                    <button v-if="props.params.isCancelable" type="button" class="btn-close" @click="() => close()"
                        aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    {{ props.params.message }}
                </div>
                <div class="modal-footer">
                    <button v-for="button in props.params.buttons" type="button" class="btn"
                        :class="buttonClass(button)" @click="() => closeAndAction(button)">
                        {{ button.title }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>