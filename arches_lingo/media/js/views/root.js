import createVueApplication from 'arches/arches/app/media/js/utils/create-vue-application';

import { createRouter, createWebHistory } from 'vue-router';

import ArchesLingo from '@/arches_lingo/ArchesLingo.vue';
import { routes } from '@/arches_lingo/routes.ts';

const router = createRouter({
    history: createWebHistory(),
    routes,
});

createVueApplication(ArchesLingo).then(vueApp => {
    vueApp.use(router);
    vueApp.mount('#lingo-mounting-point');
});
