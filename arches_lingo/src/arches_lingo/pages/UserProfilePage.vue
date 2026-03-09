<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Card from "primevue/card";
import Divider from "primevue/divider";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Password from "primevue/password";
import Skeleton from "primevue/skeleton";

import {
    fetchUserProfile,
    updateUserProfile,
    changePassword,
} from "@/arches_lingo/api.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    ERROR,
    SUCCESS,
} from "@/arches_lingo/constants.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

import type { User } from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();
const toast = useToast();

const userStore = useUserStore();

// Profile form state
const isLoading = ref(true);
const isSavingProfile = ref(false);
const profile = ref<User>({
    username: "",
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    is_lingo_editor: false,
    is_anonymous: true,
});

// Password form state
const isSavingPassword = ref(false);
const oldPassword = ref("");
const newPassword = ref("");
const confirmPassword = ref("");
const passwordMessage = ref("");
const passwordMessageSeverity = ref<"success" | "error">("success");

onMounted(async () => {
    try {
        profile.value = await fetchUserProfile();
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to load profile"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isLoading.value = false;
    }
});

async function saveProfile() {
    isSavingProfile.value = true;
    try {
        const updated = await updateUserProfile({
            first_name: profile.value.first_name,
            last_name: profile.value.last_name,
            email: profile.value.email,
            phone: profile.value.phone,
        });
        profile.value = updated;
        userStore.setUser(updated);

        toast.add({
            severity: SUCCESS,
            life: DEFAULT_TOAST_LIFE,
            summary: $gettext("Profile updated"),
            detail: $gettext("Your profile has been saved successfully."),
        });
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to update profile"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isSavingProfile.value = false;
    }
}

async function submitPasswordChange() {
    passwordMessage.value = "";

    if (!oldPassword.value || !newPassword.value || !confirmPassword.value) {
        passwordMessage.value = $gettext("All password fields are required.");
        passwordMessageSeverity.value = "error";
        return;
    }

    if (newPassword.value !== confirmPassword.value) {
        passwordMessage.value = $gettext(
            "New password and confirmation must match.",
        );
        passwordMessageSeverity.value = "error";
        return;
    }

    isSavingPassword.value = true;
    try {
        const result = await changePassword(
            oldPassword.value,
            newPassword.value,
            confirmPassword.value,
        );
        passwordMessage.value = result.success;
        passwordMessageSeverity.value = "success";
        oldPassword.value = "";
        newPassword.value = "";
        confirmPassword.value = "";
    } catch (error) {
        passwordMessage.value =
            error instanceof Error
                ? error.message
                : $gettext("An error occurred.");
        passwordMessageSeverity.value = "error";
    } finally {
        isSavingPassword.value = false;
    }
}
</script>

<template>
    <div class="profile-page">
        <div class="profile-header">
            <h1 class="page-title">
                <i
                    class="pi pi-user"
                    aria-hidden="true"
                />
                {{ $gettext("My Profile") }}
            </h1>
            <p class="page-subtitle">
                {{
                    $gettext(
                        "Manage your account information and security settings.",
                    )
                }}
            </p>
        </div>

        <div class="profile-content">
            <!-- Profile Information -->
            <Card class="profile-card">
                <template #title>
                    <div class="card-title">
                        <i
                            class="pi pi-id-card"
                            aria-hidden="true"
                        />
                        {{ $gettext("Personal Information") }}
                    </div>
                </template>
                <template #content>
                    <div
                        v-if="isLoading"
                        class="skeleton-form"
                    >
                        <Skeleton
                            height="2.5rem"
                            class="skeleton-field"
                        />
                        <Skeleton
                            height="2.5rem"
                            class="skeleton-field"
                        />
                        <Skeleton
                            height="2.5rem"
                            class="skeleton-field"
                        />
                        <Skeleton
                            height="2.5rem"
                            class="skeleton-field"
                        />
                        <Skeleton
                            height="2.5rem"
                            class="skeleton-field"
                        />
                    </div>

                    <form
                        v-else
                        class="profile-form"
                        @submit.prevent="saveProfile"
                    >
                        <div class="form-field">
                            <label for="username">{{
                                $gettext("Username")
                            }}</label>
                            <InputText
                                id="username"
                                v-model="profile.username"
                                :disabled="true"
                                class="form-input"
                            />
                            <small class="field-hint">{{
                                $gettext("Username cannot be changed.")
                            }}</small>
                        </div>

                        <div class="form-row">
                            <div class="form-field">
                                <label for="first_name">{{
                                    $gettext("First Name")
                                }}</label>
                                <InputText
                                    id="first_name"
                                    v-model="profile.first_name"
                                    class="form-input"
                                    :placeholder="$gettext('First name')"
                                />
                            </div>
                            <div class="form-field">
                                <label for="last_name">{{
                                    $gettext("Last Name")
                                }}</label>
                                <InputText
                                    id="last_name"
                                    v-model="profile.last_name"
                                    class="form-input"
                                    :placeholder="$gettext('Last name')"
                                />
                            </div>
                        </div>

                        <div class="form-field">
                            <label for="email">{{ $gettext("Email") }}</label>
                            <InputText
                                id="email"
                                v-model="profile.email"
                                type="email"
                                class="form-input"
                                :placeholder="$gettext('Email address')"
                            />
                        </div>

                        <div class="form-field">
                            <label for="phone">{{ $gettext("Phone") }}</label>
                            <InputText
                                id="phone"
                                v-model="profile.phone"
                                class="form-input"
                                :placeholder="
                                    $gettext('Phone number (optional)')
                                "
                            />
                        </div>

                        <div class="form-actions">
                            <Button
                                type="submit"
                                :label="$gettext('Save Profile')"
                                :loading="isSavingProfile"
                                icon="pi pi-check"
                            />
                        </div>
                    </form>
                </template>
            </Card>

            <!-- Change Password -->
            <Card class="profile-card">
                <template #title>
                    <div class="card-title">
                        <i
                            class="pi pi-lock"
                            aria-hidden="true"
                        />
                        {{ $gettext("Change Password") }}
                    </div>
                </template>
                <template #content>
                    <form
                        class="profile-form"
                        @submit.prevent="submitPasswordChange"
                    >
                        <Message
                            v-if="passwordMessage"
                            :severity="passwordMessageSeverity"
                            :closable="true"
                            @close="passwordMessage = ''"
                        >
                            {{ passwordMessage }}
                        </Message>

                        <div class="form-field">
                            <label for="old_password">{{
                                $gettext("Current Password")
                            }}</label>
                            <Password
                                id="old_password"
                                v-model="oldPassword"
                                :feedback="false"
                                toggle-mask
                                class="form-input"
                                :placeholder="$gettext('Current password')"
                                input-class="form-input"
                            />
                        </div>

                        <Divider />

                        <div class="form-field">
                            <label for="new_password">{{
                                $gettext("New Password")
                            }}</label>
                            <Password
                                id="new_password"
                                v-model="newPassword"
                                toggle-mask
                                class="form-input"
                                :placeholder="$gettext('New password')"
                                input-class="form-input"
                            />
                        </div>

                        <div class="form-field">
                            <label for="confirm_password">{{
                                $gettext("Confirm New Password")
                            }}</label>
                            <Password
                                id="confirm_password"
                                v-model="confirmPassword"
                                :feedback="false"
                                toggle-mask
                                class="form-input"
                                :placeholder="$gettext('Confirm new password')"
                                input-class="form-input"
                            />
                        </div>

                        <div class="form-actions">
                            <Button
                                type="submit"
                                :label="$gettext('Update Password')"
                                :loading="isSavingPassword"
                                severity="secondary"
                                icon="pi pi-lock"
                            />
                        </div>
                    </form>
                </template>
            </Card>
        </div>
    </div>
</template>

<style scoped>
.profile-page {
    height: 100%;
    overflow-y: auto;
    padding: 2rem;
    font-family: var(--p-lingo-font-family);
}

.profile-header {
    margin-bottom: 2rem;
}

.page-title {
    margin: 0;
    font-size: 1.5rem;
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-text-color);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.page-title i {
    font-size: 1.25rem;
}

.page-subtitle {
    margin: 0.25rem 0 0 0;
    font-size: var(--p-lingo-font-size-normal);
    color: var(--p-text-muted-color);
}

.profile-content {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    max-width: 40rem;
}

.profile-card {
    border-radius: 0.25rem;
}

.card-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.1rem;
    font-weight: 600;
}

.card-title i {
    font-size: 1rem;
    color: var(--p-primary-color);
}

.skeleton-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.skeleton-field {
    width: 100%;
}

.profile-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.form-row {
    display: flex;
    gap: 1rem;
}

.form-row .form-field {
    flex: 1;
}

.form-field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.form-field label {
    font-size: var(--p-lingo-font-size-small);
    font-weight: 600;
    color: var(--p-text-color);
}

.form-input {
    width: 100%;
}

.field-hint {
    font-size: 0.75rem;
    color: var(--p-text-muted-color);
}

.form-actions {
    display: flex;
    justify-content: flex-end;
    padding-top: 0.5rem;
}

.form-actions :deep(.p-button) {
    border-radius: 0.125rem;
}

@media screen and (max-width: 600px) {
    .profile-page {
        padding: 1rem;
    }

    .form-row {
        flex-direction: column;
    }
}
</style>
