import createVueApplication from 'arches/arches/app/media/js/utils/create-vue-application';
import { ArchesPreset, DEFAULT_THEME } from '@/arches/themes/default.ts';

import { definePreset } from '@primevue/themes';
import { createRouter, createWebHistory } from 'vue-router';

import LingoApp from '@/arches_lingo/App.vue';
import { routes } from '@/arches_lingo/routes.ts';

const router = createRouter({
    history: createWebHistory(),
    routes,
});

const LingoPreset = definePreset(ArchesPreset, {
    components: {
        button: {
            root: {
                label: {
                    fontWeight: 600,
                },
            },
        },
    },
});

const LingoTheme = {
    theme: {
        ...DEFAULT_THEME,
        preset: LingoPreset,
    },
};

createVueApplication(LingoApp, LingoTheme).then(vueApp => {
    vueApp.use(router);
    vueApp.mount('#lingo-mounting-point');
});
