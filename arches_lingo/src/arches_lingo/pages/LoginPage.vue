<script setup lang="ts">
import LoginForm from "@/arches_lingo/components/login/LoginForm.vue";
</script>

<template>
    <div class="login-container">
        <LoginForm />
        <div class="spacer"></div>
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
    background: var(--p-form-field-disabled-background);
}

.spacer {
    height: 4rem;
}
</style>
