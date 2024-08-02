<script setup lang="ts">
import { ref } from "vue";

import Toast from "primevue/toast";

import HomePage from "@/arches_lingo/components/HomePage.vue";
import LoginPage from "@/arches_lingo/components/LoginPage.vue";

import type { User } from "@/arches_lingo/types";

const user = ref<User | null>(null);
</script>

<template>
    <component
        :is="user ? HomePage : LoginPage"
        v-model="user"
    />
    <Toast />
</template>
