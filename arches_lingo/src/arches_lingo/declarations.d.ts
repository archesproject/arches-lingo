// declare untyped modules that have been added to your project in `package.json`
// Module homepage on npmjs.com uses logos "TS" or "DT" to indicate if typed

import("@/arches/declarations.d.ts");

declare module "primevue/toasteventbus" {
    import type { ToastMessageOptions } from "primevue/toast";

    const ToastEventBus: {
        on(event: "add", handler: (message: ToastMessageOptions) => void): void;
        off(
            event: "add",
            handler: (message: ToastMessageOptions) => void,
        ): void;
    };
    export default ToastEventBus;
}
