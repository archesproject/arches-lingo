import { ref } from "vue";

const KEYS_TO_TARGET_INDEX: Record<
    string,
    (focusedIndex: number, lastIndex: number) => number
> = {
    ArrowDown: (focusedIndex, lastIndex) =>
        Math.min(focusedIndex + 1, lastIndex),
    ArrowUp: (focusedIndex) => Math.max(focusedIndex - 1, 0),
    Home: () => 0,
    End: (_focusedIndex, lastIndex) => lastIndex,
};

export function useRovingListFocus(getFocusableItems: () => HTMLElement[]) {
    const activeItemIndex = ref(0);

    function getItemTabIndex(itemIndex: number) {
        return itemIndex === activeItemIndex.value ? 0 : -1;
    }

    function focusItem(itemIndex: number) {
        activeItemIndex.value = itemIndex;
        getFocusableItems()[itemIndex]?.focus();
    }

    function onListFocusIn(event: FocusEvent) {
        const focusedItemIndex = getFocusableItems().findIndex((item) =>
            item.contains(event.target as Node),
        );

        if (focusedItemIndex >= 0) {
            activeItemIndex.value = focusedItemIndex;
        }
    }

    function onListKeydown(event: KeyboardEvent) {
        const focusableItems = getFocusableItems();
        const focusedItemIndex = focusableItems.findIndex(
            (item) => item === event.target,
        );
        const getTargetIndex = KEYS_TO_TARGET_INDEX[event.key];

        if (focusedItemIndex < 0 || !getTargetIndex) {
            return;
        }

        event.preventDefault();
        focusItem(getTargetIndex(focusedItemIndex, focusableItems.length - 1));
    }

    return {
        activeItemIndex,
        getItemTabIndex,
        focusItem,
        onListFocusIn,
        onListKeydown,
    };
}
