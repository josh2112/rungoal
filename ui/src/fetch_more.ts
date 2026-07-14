import { onBeforeUnmount, onMounted, type Ref } from 'vue';

export function useFetchMore(targetRef: Ref<Element | undefined>, callback: () => Promise<void>, margin_px?: number) {
    let observer: IntersectionObserver | null = null;

    onMounted(() => {
        observer = new IntersectionObserver(
            (entries) => {
                // If the sentinel is visible, trigger the callback
                if (entries[0].isIntersecting) {
                    callback()
                }
            },
            { rootMargin: `${margin_px ?? 200}px` }
        )

        if (targetRef.value) {
            observer.observe(targetRef.value)
        }
    })

    onBeforeUnmount(() => {
        if (observer) observer.disconnect()
    })
}