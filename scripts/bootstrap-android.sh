#!/usr/bin/env bash
# Recreate APK build pieces that are generated or binary (wrapper jar, offline JSON).
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
export PATH="${HOME}/.local/bin:${PATH}"

wrapper="$root/web/android/gradle/wrapper/gradle-wrapper.jar"
if [[ ! -f "$wrapper" ]]; then
  echo "Downloading Gradle 8.11.1 wrapper jar…"
  curl -fsSL -o "$wrapper" \
    "https://github.com/gradle/gradle/raw/v8.11.1/gradle/wrapper/gradle-wrapper.jar"
fi

sixman-rank export-offline --out web/public/offline
cd web
npm install
npm run android:sync
echo "Android project synced. Open with: npx cap open android"
