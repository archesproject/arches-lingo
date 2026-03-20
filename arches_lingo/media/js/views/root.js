import createVueApplication from 'arches/arches/app/media/js/utils/create-vue-application';

import { createPinia } from 'pinia';
import { createRouter, createWebHistory } from 'vue-router';

import ArchesLingo from '@/arches_lingo/ArchesLingo.vue';
import { routes } from '@/arches_lingo/routes.ts';
import { LingoTheme } from '@/arches_lingo/themes/lingo_theme.ts';
import { useUserStore } from '@/arches_lingo/stores/useUserStore.ts';
import { useAppSettingsStore } from '@/arches_lingo/stores/useAppSettingsStore.ts';
import { routeNames } from '@/arches_lingo/routes.ts';

const pinia = createPinia();

const router = createRouter({
    history: createWebHistory(),
    routes,
});

router.beforeEach(async (to, _from, next) => {
    if (to.name === routeNames.login) return next();

    const userStore = useUserStore(pinia);
    const appSettingsStore = useAppSettingsStore(pinia);

    await Promise.allSettled([
        userStore.refresh(),
        appSettingsStore.initialize(),
    ]);

    const requiresAuth = to.matched.some(
        (record) => record.meta.requiresAuthentication,
    );

    if (userStore.isAnonymous && (!appSettingsStore.allowAnonymousAccess || requiresAuth)) {
        return next({ name: routeNames.login });
    }

    next();
});

createVueApplication(ArchesLingo, LingoTheme).then(async (vueApp) => {
    vueApp.use(pinia);
    vueApp.use(router);

    await router.isReady();
    vueApp.mount('#lingo-mounting-point');
});
