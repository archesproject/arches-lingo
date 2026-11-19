import createVueApplication from 'arches/arches/app/media/js/utils/create-vue-application';

import { createPinia } from 'pinia';
import { createRouter, createWebHistory } from 'vue-router';

import ArchesLingo from '@/arches_lingo/ArchesLingo.vue';
import { routes } from '@/arches_lingo/routes.ts';
import { LingoTheme } from '@/arches_lingo/themes/lingo_theme.ts';
import { applyHighContrast, isHighContrastPreferred } from '@/arches_lingo/themes/high_contrast.ts';
import { useUserStore } from '@/arches_lingo/stores/useUserStore.ts';
import { useAppSettingsStore } from '@/arches_lingo/stores/useAppSettingsStore.ts';
import { routeNames } from '@/arches_lingo/routes.ts';
import { getSafeNextPath } from '@/arches_lingo/utils.ts';

applyHighContrast(isHighContrastPreferred());

applyHighContrast(isHighContrastPreferred());

const pinia = createPinia();

const router = createRouter({
    history: createWebHistory(),
    routes,
});

router.beforeEach(async (to, from, next) => {
    const userStore = useUserStore(pinia);
    const appSettingsStore = useAppSettingsStore(pinia);

    // Query-only navigations (tree clicks, filter keystrokes, match-review
    // paging) stay on the same page, so they reuse the user fetched for it.
    // The first navigation has no matched records and always refreshes.
    const isSamePageNavigation =
        from.matched.length > 0 && to.path === from.path;

    await Promise.allSettled([
        isSamePageNavigation ? Promise.resolve() : userStore.refresh(),
        appSettingsStore.initialize(),
    ]);

    if (to.name === routeNames.login && !userStore.isAnonymous) {
        return next(getSafeNextPath(to.query.next) ?? { name: routeNames.dashboard });
    }

    const isAlwaysPublic = to.matched.some((record) => record.meta.alwaysPublic);
    if (isAlwaysPublic) return next();

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
