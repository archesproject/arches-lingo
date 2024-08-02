<script setup lang="ts">
import arches from "arches";
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import InputText from "primevue/inputtext";
import Button from "primevue/button";

import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";
import { login } from "@/arches_lingo/api.ts";

import type { User } from "@/arches_lingo/types";

const { $gettext } = useGettext();
const toast = useToast();

const user = defineModel<User | null>({ required: true });
const username = ref();
const password = ref();

const submit = async () => {
    try {
        user.value = await login(username.value, password.value);
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
    <div style="margin: 5%">
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
        <div
            class="spacer"
            style="height: 10rem"
        ></div>
        <div style="display: flex; justify-content: space-between; width: 30%">
            <Button
                as="a"
                :label="$gettext('Register')"
                :href="arches.urls.signup"
            />
            <Button
                as="a"
                :label="$gettext('Multi-factor login')"
                :href="arches.urls.auth"
            />
        </div>
    </div>
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
