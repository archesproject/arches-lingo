import { afterEach, describe, expect, it } from "vitest";

import { useRovingListFocus } from "@/arches_lingo/composables/useRovingListFocus.ts";

function renderLinks(linkCount: number) {
    const list = document.createElement("ul");
    for (let linkIndex = 0; linkIndex < linkCount; linkIndex++) {
        const listItem = document.createElement("li");
        const link = document.createElement("a");
        link.href = `#${linkIndex}`;
        listItem.appendChild(link);
        list.appendChild(listItem);
    }
    document.body.appendChild(list);
    return [...list.querySelectorAll("a")];
}

function pressKey(target: HTMLElement, key: string) {
    const event = new KeyboardEvent("keydown", { key, cancelable: true });
    Object.defineProperty(event, "target", { value: target });
    return event;
}

describe("useRovingListFocus", () => {
    afterEach(() => {
        document.body.innerHTML = "";
    });

    it("keeps only the active item in the tab order", () => {
        const { getItemTabIndex } = useRovingListFocus(() => []);

        expect(getItemTabIndex(0)).toBe(0);
        expect(getItemTabIndex(1)).toBe(-1);
    });

    it("moves focus with the arrow, Home and End keys", () => {
        const links = renderLinks(3);
        const { activeItemIndex, onListKeydown } = useRovingListFocus(
            () => links,
        );

        onListKeydown(pressKey(links[0], "ArrowDown"));
        expect(document.activeElement).toBe(links[1]);

        onListKeydown(pressKey(links[1], "End"));
        expect(document.activeElement).toBe(links[2]);

        onListKeydown(pressKey(links[2], "ArrowDown"));
        expect(document.activeElement).toBe(links[2]);

        onListKeydown(pressKey(links[2], "Home"));
        expect(document.activeElement).toBe(links[0]);
        expect(activeItemIndex.value).toBe(0);
    });

    it("ignores keys pressed on controls inside an item", () => {
        const links = renderLinks(2);
        const { onListKeydown } = useRovingListFocus(() => links);
        const event = pressKey(links[0].parentElement as HTMLElement, "End");

        onListKeydown(event);

        expect(event.defaultPrevented).toBe(false);
    });

    it("makes the item that receives focus the tab stop", () => {
        const links = renderLinks(3);
        const { activeItemIndex, onListFocusIn } = useRovingListFocus(
            () => links,
        );
        const event = new FocusEvent("focusin");
        Object.defineProperty(event, "target", { value: links[2] });

        onListFocusIn(event);

        expect(activeItemIndex.value).toBe(2);
    });
});
