<script setup lang="ts">
import DisplaySettingsMenu from "@/arches_lingo/components/generic/DisplaySettingsMenu.vue";
import LoginForm from "@/arches_lingo/components/login/LoginForm.vue";
</script>

<template>
    <div class="login-container">
        <DisplaySettingsMenu class="login-display-settings" />
        <LoginForm />
        <div class="spacer"></div>
    </div>
</template>

<style scoped>
.login-container {
    position: relative;
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

.login-display-settings {
    position: absolute;
    top: 1rem;
    inset-inline-end: 1rem;
}

.spacer {
    height: 4rem;
}
</style>
