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
    justify-content: safe center;
    align-items: center;
    box-sizing: border-box;
    height: 100%;
    background: var(--p-form-field-disabled-background);
    overflow: auto;
    padding: 1rem 1rem 12rem;
    @media (max-width: 960px) {
        padding-bottom: 1rem;
    }
}

.spacer {
    height: 4rem;
}
</style>
