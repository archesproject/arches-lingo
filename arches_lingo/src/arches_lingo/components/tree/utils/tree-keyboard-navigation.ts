const TREE_ITEM_SELECTOR = '[role="treeitem"]';

/**
 * Adds keys PrimeVue's Tree lacks: Home and End (APG tree view), and
 * type-to-filter, which hands printable characters to `onTypeahead` so the
 * tree's filter input can take over. Bind the handler to the Tree root's
 * keydown.
 *
 * Collapsed nodes' children are not rendered, so every treeitem in the DOM is
 * a visible node; End lands on the last one without opening anything.
 */
export function useTreeKeyboardNavigation(
    onTypeahead: (character: string) => void,
) {
    function moveFocus(fromTreeItem: HTMLElement, toTreeItem: HTMLElement) {
        fromTreeItem.tabIndex = -1;
        toTreeItem.tabIndex = 0;
        toTreeItem.focus();
    }

    function isTypeaheadKey(event: KeyboardEvent) {
        // Space belongs to PrimeVue (it selects the node).
        return event.key.length === 1 && event.key !== " ";
    }

    function onTreeKeydown(event: KeyboardEvent) {
        const focusedTreeItem = event.target as HTMLElement;

        if (
            !focusedTreeItem.matches(TREE_ITEM_SELECTOR) ||
            event.ctrlKey ||
            event.metaKey ||
            event.altKey
        ) {
            return;
        }

        if (event.key === "Home" || event.key === "End") {
            const treeRootElement = event.currentTarget as HTMLElement;
            const visibleTreeItems = [
                ...treeRootElement.querySelectorAll<HTMLElement>(
                    TREE_ITEM_SELECTOR,
                ),
            ];
            const targetTreeItem =
                event.key === "Home"
                    ? visibleTreeItems[0]
                    : visibleTreeItems[visibleTreeItems.length - 1];

            event.preventDefault();
            if (targetTreeItem && targetTreeItem !== focusedTreeItem) {
                moveFocus(focusedTreeItem, targetTreeItem);
            }
            return;
        }

        if (isTypeaheadKey(event)) {
            event.preventDefault();
            onTypeahead(event.key);
        }
    }

    return { onTreeKeydown };
}
