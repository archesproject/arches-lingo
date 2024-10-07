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
        <h1>{{ $gettext("LINGO") }}</h1>
        <h2>{{ $gettext("Vocabulary management powered by Arches.") }}</h2>
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
    </form>
</template>

<style scoped>
form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    width: 30%;
}

input {
    width: 100%;
}
</style>
