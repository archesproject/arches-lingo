<script setup lang="ts">
import LoginForm from "@/arches_lingo/components/login/LoginForm.vue";
import LoginLinks from "@/arches_lingo/components/login/LoginLinks.vue";
</script>

<template>
    <div class="login-container">
        <LoginForm />
        <div class="spacer" />
        <LoginLinks />
    </div>
</template>

<style scoped>
.login-container {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 100%;
    padding-bottom: 12rem;
}

.spacer {
    height: 4rem;
}
</style>
