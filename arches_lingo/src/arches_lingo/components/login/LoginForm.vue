<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import InputText from "primevue/inputtext";
import Button from "primevue/button";

import { login } from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

import LoginLinks from "@/arches_lingo/components/login/LoginLinks.vue";

const { $gettext } = useGettext();
const toast = useToast();
const router = useRouter();
const route = useRoute();

const username = ref();
const password = ref();

const submit = async () => {
    try {
        await login(username.value, password.value);
        router.push(route.redirectedFrom || { name: routeNames.root });
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Sign in failed."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
};
</script>

<template>
    <form>
        <div class="form-header">
            <h1>{{ $gettext("LINGO") }}</h1>
            <h2>
                {{
                    $gettext(
                        "Vocabulary and authority data management powered by Arches.",
                    )
                }}
            </h2>
        </div>
        <div class="main-form">
            <InputText
                v-model="username"
                :placeholder="$gettext('Username')"
                :aria-label="$gettext('Username')"
                autocomplete="username"
            />
            <InputText
                v-model="password"
                :placeholder="$gettext('Password')"
                :aria-label="$gettext('Password')"
                type="password"
                autocomplete="password"
                @keyup.enter="submit"
            />
            <Button
                type="button"
                :label="$gettext('Sign In')"
                @click="submit"
            />
        </div>
        <div class="form-footer">
            <h2>
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
    font-family: "Lucida Sans", "Lucida Sans Regular", "Lucida Grande",
        "Lucida Sans Unicode", Geneva, Verdana, sans-serif;
    display: flex;
    flex-direction: column;
    padding: 2rem 2rem;
    gap: 1rem;
    width: 25rem;
    background: var(--p-inputtext-background);
    border-radius: 0.25rem;
    box-shadow:
        0 0 1rem 0.375rem rgba(20, 20, 20, 0.125),
        0 1.5rem 1.25rem 0 rgba(0, 0, 0, 0.19);
}

.form-header {
    padding: 0.5rem 0;
}

h1 {
    margin: 0;
    font-weight: 400;
    color: var(--p-inputtext-color);
}

h2 {
    margin: 0;
    font-weight: 400;
    font-size: 1rem;
    color: var(--p-inputtext-hover-border-color);
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
    font-size: 0.95rem;
}
</style>
