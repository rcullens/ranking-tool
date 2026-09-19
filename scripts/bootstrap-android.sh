#!/usr/bin/env bash
# Recreate APK build pieces that are generated or binary (wrapper jar, icons, offline JSON).
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
export PATH="${HOME}/.local/bin:${PATH}"

python3 "$root/scripts/generate_android_assets.py"

wrapper="$root/web/android/gradle/wrapper/gradle-wrapper.jar"
if [[ ! -f "$wrapper" ]]; then
  echo "Downloading Gradle 8.11.1 wrapper jar…"
  mkdir -p "$(dirname "$wrapper")"
  curl -fsSL -o "$wrapper" \
    "https://raw.githubusercontent.com/gradle/gradle/v8.11.1/gradle/wrapper/gradle-wrapper.jar"
fi

sixman-rank export-offline --out web/public/offline
cd web
npm install
npm run android:sync
echo "Android project synced. Open with: npx cap open android"
echo "Then Build → Build APK(s), or: ./scripts/build-apk.sh"
echo "APK lands at: web/android/app/build/outputs/apk/debug/app-debug.apk"
