<script setup lang="ts">
import { provide, ref } from "vue";

import Toast from "primevue/toast";

import { userKey } from "@/arches_lingo/constants.ts";
import HomePage from "@/arches_lingo/components/HomePage.vue";
import LoginPage from "@/arches_lingo/components/login/LoginPage.vue";

import type { User } from "@/arches_lingo/types";

const user = ref<User | null>(null);
const setUser = (userToSet: User | null) => {
    user.value = userToSet;
};
provide(userKey, { user, setUser });
</script>

<template>
    <component
        :is="user ? HomePage : LoginPage"
        v-model="user"
    />
    <Toast />
</template>
