#!/usr/bin/env python3
"""Regression checks for optional local.properties and CI configuration inputs."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "local.properties"
GENERATED = ROOT / "composeApp/build/generated/runtime-config/kotlin/com/nuvio/app"

# Environment key -> generated file and constant. Check every supported integration.
CONFIGS = {
    "TRAKT_CLIENT_ID": ("features/trakt/TraktConfig.kt", "CLIENT_ID"),
    "TRAKT_CLIENT_SECRET": ("features/trakt/TraktConfig.kt", "CLIENT_SECRET"),
    "TRAKT_REDIRECT_URI": ("features/trakt/TraktConfig.kt", "REDIRECT_URI"),
    "SIMKL_CLIENT_ID": ("features/simkl/SimklConfig.kt", "CLIENT_ID"),
    "SIMKL_REDIRECT_URI": ("features/simkl/SimklConfig.kt", "REDIRECT_URI"),
    "SIMKL_APP_NAME": ("features/simkl/SimklConfig.kt", "APP_NAME"),
    "MDBLIST_CLIENT_ID": ("features/mdblist/MdbListConfig.kt", "CLIENT_ID"),
    "INTRODB_API_URL": ("features/player/skip/IntroDbConfig.kt", "URL"),
    "IMDB_RATINGS_API_BASE_URL": ("features/details/ImdbEpisodeRatingsConfig.kt", "IMDB_RATINGS_API_BASE_URL"),
    "IMDB_TAPFRAME_API_BASE_URL": ("features/details/ImdbEpisodeRatingsConfig.kt", "IMDB_TAPFRAME_API_BASE_URL"),
    "OMDB_API_KEY": ("features/details/ImdbEpisodeRatingsConfig.kt", "OMDB_API_KEY"),
    "PREMIUMIZE_CLIENT_ID": ("features/debrid/PremiumizeConfig.kt", "CLIENT_ID"),
    "CONTRIBUTIONS_URL": ("features/settings/CommunityConfig.kt", "CONTRIBUTIONS_URL"),
    "SUPPORTERS_WALL_URL": ("features/settings/CommunityConfig.kt", "SUPPORTERS_WALL_URL"),
    "DONATIONS_BASE_URL": ("features/settings/CommunityConfig.kt", "DONATIONS_BASE_URL"),
    "DONATIONS_DONATE_URL": ("features/settings/CommunityConfig.kt", "DONATIONS_DONATE_URL"),
    "NUVIO_SUPABASE_URL": ("core/network/SupabaseConfig.kt", "URL"),
    "NUVIO_SUPABASE_ANON_KEY": ("core/network/SupabaseConfig.kt", "ANON_KEY"),
    "NUVIO_SUPABASE_FALLBACK_URL": ("core/network/SupabaseConfig.kt", "FALLBACK_URL"),
    "SENTRY_DSN": ("core/diagnostics/SentryConfig.kt", "DSN"),
    "SENTRY_ENVIRONMENT": ("core/diagnostics/SentryConfig.kt", "ENVIRONMENT"),
    "TMDB_API_KEY": ("features/tmdb/TmdbConfig.kt", "API_KEY"),
}


def generate(environment, expected):
    subprocess.run(
        ["./gradlew", ":composeApp:generateRuntimeConfigs", "--stacktrace"],
        cwd=ROOT, env=environment, check=True,
    )
    for key, value in expected.items():
        filename, constant = CONFIGS[key]
        literal = json.dumps(value, ensure_ascii=False).replace("$", "\\$")
        if f"const val {constant} = {literal}" not in (GENERATED / filename).read_text():
            raise AssertionError(f"Incorrect generated value for {key}")
    print("All integration configs verified.", flush=True)


def main():
    original = LOCAL.read_bytes() if LOCAL.exists() else None
    values = {key: "ci-" + key.lower() for key in CONFIGS}
    # Quotes, backslashes, interpolation and newlines must produce valid Kotlin literals.
    values["TRAKT_CLIENT_SECRET"] = 'quote" slash\\ dollar$ newline\nend'
    environment = dict(os.environ, **values)
    try:
        LOCAL.unlink(missing_ok=True)
        generate(environment, values)
        assert not LOCAL.exists(), "The generator must not create local.properties"

        LOCAL.write_text("TRAKT_CLIENT_ID=local-trakt\nTMDB_API_KEY=local-tmdb\nSIMKL_CLIENT_ID=   \n")
        generate(environment, dict(values, TRAKT_CLIENT_ID="local-trakt", TMDB_API_KEY="local-tmdb"))

        LOCAL.unlink()
        values["TRAKT_CLIENT_ID"] = "changed-ci-trakt"
        environment.update(values)
        generate(environment, values)
        assert not LOCAL.exists()
        defaults = {key: "" for key in CONFIGS}
        defaults.update(
            TRAKT_REDIRECT_URI="nuvio://auth/trakt",
            SIMKL_REDIRECT_URI="nuvio://auth/simkl",
            SIMKL_APP_NAME="nuvio",
            SUPPORTERS_WALL_URL="https://nuvio.tv/api/supporters/wall",
            SENTRY_ENVIRONMENT="production",
        )
        generate({key: value for key, value in environment.items() if key not in CONFIGS}, defaults)
        print("Missing file, environment fallback, local precedence, escaping, input invalidation and defaults passed.")
    finally:
        if original is None:
            LOCAL.unlink(missing_ok=True)
        else:
            LOCAL.write_bytes(original)


if __name__ == "__main__":
    main()
