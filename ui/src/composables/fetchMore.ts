import { nextTick, onBeforeUnmount, onMounted, type Ref } from 'vue';

export function useFetchMore(targetRef: Ref<Element | undefined>, fetchMore: () => Promise<void>, margin_px?: number) {
    let observer: IntersectionObserver | null = null;

    onMounted(() => {
        observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting) {
                    // Target ref is visible; we need more data. Fetch, wait for the new data
                    // to be rendered, then force the intersection to be checked again (in case
                    // the fetch didn't fill the screen and the targetRef is still visible)
                    fetchMore().then(() => nextTick().then(() => {
                        if (targetRef.value) {
                            observer?.unobserve(targetRef.value);
                            observer?.observe(targetRef.value);
                        }
                    }));
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