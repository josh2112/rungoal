import { Modal } from 'bootstrap';
import { onMounted, onUnmounted, type Ref } from 'vue';

export function useDialog(dialogRef: Ref<Element | undefined>) {
    let dialog: Modal | null = null;

    onMounted(() => {
        if (dialogRef.value) {
            dialog = new Modal(dialogRef.value);
        }
        else {
            console.log("shiat!")
        }
    });

    onUnmounted(() => dialog?.dispose());

    return {
        open: () => dialog?.show(),
        close: () => {
            (document.activeElement as HTMLElement)?.blur();
            dialog?.hide();
        }
    };
}