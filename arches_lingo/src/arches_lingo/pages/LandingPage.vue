<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import { generateArchesURL } from "@/arches/utils/generate-arches-url.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

const { $gettext } = useGettext();
const router = useRouter();
const userStore = useUserStore();

const userDisplayName = computed(() => {
    const user = userStore.user;
    if (!user) return "";
    return user.first_name.trim() || user.username;
});

const quickActions = [
    {
        key: "dashboard",
        label: $gettext("Dashboard"),
        description: $gettext(
            "View statistics, recent activity, and translation coverage",
        ),
        icon: "pi pi-home",
        route: { name: routeNames.dashboard },
    },
    {
        key: "schemes",
        label: $gettext("Schemes & Concepts"),
        description: $gettext(
            "Browse and manage controlled vocabularies and concept hierarchies",
        ),
        icon: "pi pi-lightbulb",
        route: { name: routeNames.schemes },
    },
    {
        key: "advanced-search",
        label: $gettext("Advanced Search"),
        description: $gettext(
            "Search across schemes, concepts, labels, and more",
        ),
        icon: "pi pi-search",
        route: { name: routeNames.advancedSearch },
    },
];

function navigateTo(route: { name: string }) {
    router.push(route);
}
</script>

<template>
    <div class="landing-page">
        <section class="landing-hero">
            <div class="hero-content">
                <div class="hero-text">
                    <img
                        :src="
                            generateArchesURL('arches_lingo:static_url') +
                            'img/arches_logo_light.png'
                        "
                        :alt="$gettext('Arches Logo')"
                        class="landing-logo"
                    />
                    <h1 class="landing-title">{{ $gettext("Lingo") }}</h1>
                    <p class="landing-subtitle">
                        {{
                            $gettext(
                                "Vocabulary and authority data management powered by Arches",
                            )
                        }}
                    </p>
                    <div
                        v-if="!userStore.isAnonymous"
                        class="authenticated-cta"
                    >
                        <p class="welcome-message">
                            {{
                                $gettext("Welcome back, %{name}!", {
                                    name: userDisplayName,
                                })
                            }}
                        </p>
                        <Button
                            :label="$gettext('Go to Dashboard')"
                            icon="pi pi-arrow-right"
                            icon-pos="right"
                            class="enter-app-button"
                            @click="router.push({ name: routeNames.dashboard })"
                        />
                    </div>
                    <Button
                        v-else
                        :label="$gettext('Sign In')"
                        icon="pi pi-sign-in"
                        class="sign-in-button"
                        @click="router.push({ name: routeNames.login })"
                    />
                </div>

                <!--
                    Inline SVG illustration representing a SKOS concept hierarchy.
                    Solid lines = single-parent hierarchical relationships (skos:broader).
                    Dashed lines = polyhierarchy — concepts with multiple broader concepts,
                    a key feature of SKOS thesauri managed by Lingo.
                -->
                <svg
                    viewBox="0 0 480 270"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                    aria-hidden="true"
                    class="knowledge-graph"
                >
                    <!-- Level 0 → Level 1 connections -->
                    <line
                        x1="240"
                        y1="45"
                        x2="95"
                        y2="130"
                        stroke="#D1DDE8"
                        stroke-width="1.5"
                    />
                    <line
                        x1="240"
                        y1="45"
                        x2="240"
                        y2="130"
                        stroke="#D1DDE8"
                        stroke-width="1.5"
                    />
                    <line
                        x1="240"
                        y1="45"
                        x2="385"
                        y2="130"
                        stroke="#D1DDE8"
                        stroke-width="1.5"
                    />

                    <!-- Level 1 → Level 2 single-parent connections -->
                    <line
                        x1="95"
                        y1="130"
                        x2="45"
                        y2="215"
                        stroke="#D1DDE8"
                        stroke-width="1.5"
                    />
                    <line
                        x1="95"
                        y1="130"
                        x2="145"
                        y2="215"
                        stroke="#D1DDE8"
                        stroke-width="1.5"
                    />
                    <line
                        x1="240"
                        y1="130"
                        x2="240"
                        y2="215"
                        stroke="#D1DDE8"
                        stroke-width="1.5"
                    />
                    <line
                        x1="385"
                        y1="130"
                        x2="335"
                        y2="215"
                        stroke="#D1DDE8"
                        stroke-width="1.5"
                    />
                    <line
                        x1="385"
                        y1="130"
                        x2="435"
                        y2="215"
                        stroke="#D1DDE8"
                        stroke-width="1.5"
                    />

                    <!-- Polyhierarchy connections (dashed) -->
                    <line
                        x1="240"
                        y1="130"
                        x2="145"
                        y2="215"
                        stroke="#A1B6CB"
                        stroke-width="1.5"
                        stroke-dasharray="4 3"
                    />
                    <line
                        x1="240"
                        y1="130"
                        x2="335"
                        y2="215"
                        stroke="#A1B6CB"
                        stroke-width="1.5"
                        stroke-dasharray="4 3"
                    />

                    <!-- Level 2 nodes -->
                    <circle
                        cx="45"
                        cy="215"
                        r="11"
                        fill="#A1B6CB"
                    />
                    <circle
                        cx="145"
                        cy="215"
                        r="11"
                        fill="#A1B6CB"
                    />
                    <circle
                        cx="240"
                        cy="215"
                        r="11"
                        fill="#A1B6CB"
                    />
                    <circle
                        cx="335"
                        cy="215"
                        r="11"
                        fill="#A1B6CB"
                    />
                    <circle
                        cx="435"
                        cy="215"
                        r="11"
                        fill="#A1B6CB"
                    />

                    <!-- Level 1 nodes -->
                    <circle
                        cx="95"
                        cy="130"
                        r="17"
                        fill="#486A8B"
                    />
                    <circle
                        cx="240"
                        cy="130"
                        r="17"
                        fill="#486A8B"
                    />
                    <circle
                        cx="385"
                        cy="130"
                        r="17"
                        fill="#486A8B"
                    />

                    <!-- Root node animated pulse ring -->
                    <circle
                        cx="240"
                        cy="45"
                        r="30"
                        fill="none"
                        stroke="#4682b4"
                        stroke-width="1"
                        class="pulse-ring"
                    />
                    <!-- Root node -->
                    <circle
                        cx="240"
                        cy="45"
                        r="22"
                        fill="#4682b4"
                    />
                </svg>
            </div>
        </section>

        <section class="landing-cards-section">
            <div class="action-cards">
                <button
                    v-for="action in quickActions"
                    :key="action.key"
                    class="action-card"
                    @click="navigateTo(action.route)"
                >
                    <span class="action-card-icon-wrap">
                        <i :class="[action.icon, 'action-card-icon']" />
                    </span>
                    <span class="action-card-label">{{ action.label }}</span>
                    <span class="action-card-description">{{
                        action.description
                    }}</span>
                </button>
            </div>
        </section>
    </div>
</template>

<style scoped>
.landing-page {
    display: flex;
    flex-direction: column;
    min-height: 100%;
    overflow-y: auto;
    background: var(--p-inputtext-background);
}

/* ── Hero ──────────────────────────────────────────────────── */

.landing-hero {
    /*
     * Gradient built from Lingo's paleBlue (#d7e7f6) and lightBlueGray (#ebeef0)
     * toward off-white (#fcfcfc).  Hardcoded here because gradients require
     * specific stop values, not CSS-variable interpolation.
     */
    background: linear-gradient(155deg, #dce8f5 0%, #eef4fa 45%, #f8fafc 100%);
    border-bottom: 1px solid #d1dde8;
    padding: 3.5rem 2rem 3rem;
    flex-shrink: 0;
}

.hero-content {
    display: flex;
    align-items: center;
    gap: 3rem;
    max-width: 60rem;
    margin: 0 auto;
}

.hero-text {
    display: flex;
    flex-direction: column;
    gap: 0.875rem;
    flex: 1;
    min-width: 0;
}

.landing-logo {
    height: 3rem;
    width: auto;
    align-self: flex-start;
    /*
     * Recolour the white logo to Lingo's deepSteelBlue (#486A8B) for
     * legibility against the light hero gradient.
     * Chain: white → black (invert 100%) → mid-grey (invert 40%) →
     *        sepia → hue-rotate to blue → saturate → darken.
     */
    filter: invert(1) invert(40%) sepia(1) hue-rotate(175deg) saturate(2)
        brightness(0.9);
}

.landing-title {
    margin: 0;
    font-size: var(--p-lingo-font-size-xxlarge);
    font-weight: var(--p-lingo-font-weight-light);
    color: var(--p-text-color);
    letter-spacing: 0.08em;
    line-height: 1.1;
}

.landing-subtitle {
    margin: 0;
    font-size: var(--p-lingo-font-size-normal);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-text-muted-color);
    max-width: 30rem;
    line-height: 1.5;
}

.sign-in-button {
    align-self: flex-start;
    margin-top: 0.5rem;
}

.authenticated-cta {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-top: 0.5rem;
}

.welcome-message {
    margin: 0;
    font-size: var(--p-lingo-font-size-medium);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-text-color);
}

.enter-app-button {
    align-self: flex-start;
}

/* ── Knowledge graph illustration ──────────────────────────── */

.knowledge-graph {
    flex: 0 0 auto;
    width: 26rem;
    height: auto;
    display: block;
    /* Lingo steelBlue tinted shadow */
    filter: drop-shadow(0 0.25rem 1rem rgba(70, 130, 180, 0.15));
}

.pulse-ring {
    transform-origin: 240px 45px;
    animation: node-pulse 2.8s ease-out infinite;
}

@keyframes node-pulse {
    0% {
        transform: scale(1);
        opacity: 0.7;
    }
    70% {
        transform: scale(1.65);
        opacity: 0;
    }
    100% {
        transform: scale(1);
        opacity: 0;
    }
}

/* ── Action cards ───────────────────────────────────────────── */

.landing-cards-section {
    padding: 2.5rem 2rem;
    flex: 1;
    background: var(--p-inputtext-background);
}

.action-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.25rem;
    max-width: 60rem;
    margin: 0 auto;
}

.action-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.875rem;
    padding: 2rem 1.5rem;
    background: var(--p-inputtext-background);
    border: 1px solid #d1dde8;
    border-radius: 0.25rem;
    cursor: pointer;
    text-align: center;
    font-family: var(--p-lingo-font-family);
    box-shadow: 0 0.0625rem 0.25rem rgba(0, 0, 0, 0.06);
    transition:
        box-shadow 0.2s ease,
        border-color 0.2s ease,
        transform 0.2s ease;
}

.action-card:hover {
    /* Lingo steelBlue tinted shadow */
    box-shadow: 0 0.375rem 1rem rgba(70, 130, 180, 0.18);
    border-color: #4682b4;
    transform: translateY(-0.125rem);
}

.action-card-icon-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 3rem;
    height: 3rem;
    /* Lingo paleBlue tint background */
    background: linear-gradient(135deg, #dce8f5 0%, #eef4fa 100%);
    border-radius: 50%;
}

.action-card-icon {
    font-size: var(--p-lingo-font-size-large);
    /* Lingo steelBlue */
    color: #4682b4;
}

.action-card-label {
    font-size: var(--p-lingo-font-size-medium);
    font-weight: var(--p-lingo-font-weight-semibold);
    color: var(--p-text-color);
}

.action-card-description {
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-text-muted-color);
    line-height: 1.45;
}

/* ── Responsive ─────────────────────────────────────────────── */

@media (max-width: 900px) {
    .hero-content {
        flex-direction: column-reverse;
        text-align: center;
        align-items: center;
        gap: 2rem;
    }

    .landing-logo {
        align-self: center;
    }

    .landing-subtitle {
        max-width: unset;
    }

    .sign-in-button {
        align-self: center;
    }

    .knowledge-graph {
        width: 18rem;
    }

    .action-cards {
        grid-template-columns: 1fr;
    }
}

@media (min-width: 901px) and (max-width: 1100px) {
    .knowledge-graph {
        width: 20rem;
    }
}
</style>
