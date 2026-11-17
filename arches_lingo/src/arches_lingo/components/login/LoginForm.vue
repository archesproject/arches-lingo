<script setup lang="ts">
import { onMounted, ref, useTemplateRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import InputText from "primevue/inputtext";
import Button from "primevue/button";

import { login } from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";
import { getSafeNextPath } from "@/arches_lingo/utils.ts";

import LoginLinks from "@/arches_lingo/components/login/LoginLinks.vue";

import type { ComponentPublicInstance } from "vue";

const { $gettext } = useGettext();
const toast = useToast();
const router = useRouter();
const route = useRoute();
const userStore = useUserStore();

const username = ref();
const password = ref();
const isSubmitting = ref(false);

const usernameInput = useTemplateRef<ComponentPublicInstance>("usernameInput");
const passwordInput = useTemplateRef<ComponentPublicInstance>("passwordInput");

onMounted(() => {
    (usernameInput.value?.$el as HTMLElement | undefined)?.focus();
});

// ?next= (header Login, MFA) wins, then a guard redirect, then the dashboard
function getPostLoginDestination() {
    return (
        getSafeNextPath(route.query.next) ??
        route.redirectedFrom ?? { name: routeNames.dashboard }
    );
}

const submit = async () => {
    if (isSubmitting.value) {
        return;
    }
    isSubmitting.value = true;

    try {
        await login(username.value, password.value);
        userStore.setUser(null);
        await router.push(getPostLoginDestination());
    } catch (error) {
        password.value = "";
        (passwordInput.value?.$el as HTMLElement | undefined)?.focus();
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Sign in failed."),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isSubmitting.value = false;
    }
};
</script>

<template>
    <form @submit.prevent="submit">
        <div class="form-header">
            <h1 class="form-title">{{ $gettext("LINGO") }}</h1>
            <h2 class="form-subtitle">
                {{
                    $gettext(
                        "Vocabulary and authority data management powered by Arches.",
                    )
                }}
            </h2>
        </div>
        <div class="main-form">
            <InputText
                ref="usernameInput"
                v-model="username"
                :placeholder="$gettext('Username')"
                :aria-label="$gettext('Username')"
                autocomplete="username"
            />
            <InputText
                ref="passwordInput"
                v-model="password"
                :placeholder="$gettext('Password')"
                :aria-label="$gettext('Password')"
                type="password"
                autocomplete="current-password"
            />
            <Button
                type="submit"
                :label="$gettext('Sign In')"
                :loading="isSubmitting"
                :disabled="isSubmitting"
            />
        </div>
        <div class="form-footer">
            <h2 class="form-subtitle">
                {{
                    $gettext(
                        "Create an account or log in using multi-factor authentication",
                    )
                }}
            </h2>
            <LoginLinks />
        </div>
    </form>
</template>

<style scoped>
form {
    display: flex;
    flex-direction: column;
    padding: 2rem 2rem;
    gap: 1rem;
    box-sizing: border-box;
    width: 100%;
    max-width: 25rem;
    background: var(--p-inputtext-background);
    border-radius: 0.25rem;
    box-shadow:
        0 0.75rem 1.5rem rgba(0, 0, 0, 0.18),
        0 0.375rem 0.75rem rgba(0, 0, 0, 0.14);
}

@media (max-width: 480px) {
    form {
        padding: 1.5rem 1rem;
    }
}

.form-header {
    padding: 0.5rem 0;
}

.form-title {
    margin: 0;
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-inputtext-color);
}

.form-subtitle {
    margin: 0;
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-normal);
    color: var(--p-lingo-form-subtitle-color);
}

input {
    width: 100%;
    margin-bottom: 0.5rem;
}

button {
    height: 2.5rem;
    width: 100%;
    margin-top: 1rem;
}

.form-footer {
    margin: 1rem 0;
    padding: 0.75rem 0;
    border-top: 0.08rem solid var(--p-inputtext-border-color);
}

.form-footer h2 {
    padding-bottom: 1rem;
    font-size: var(--p-lingo-font-size-smallnormal);
}
</style>
