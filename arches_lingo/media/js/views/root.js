import createVueApplication from 'arches/arches/app/media/js/utils/create-vue-application';

import { createRouter, createWebHistory } from 'vue-router';

import ArchesLingo from '@/arches_lingo/ArchesLingo.vue';
import { routes } from '@/arches_lingo/routes.ts';
import { LingoTheme } from '@/arches_lingo/themes/lingo_theme.ts';

const router = createRouter({
    history: createWebHistory(),
    routes,
});

createVueApplication(ArchesLingo, LingoTheme).then(vueApp => {
    vueApp.use(router);
    vueApp.mount('#lingo-mounting-point');
});
