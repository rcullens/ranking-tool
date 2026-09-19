#!/usr/bin/env bash
# Build a debug APK. Requires Node, Python, and the Android SDK (ANDROID_HOME).
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
export PATH="${HOME}/.local/bin:${PATH}"

sixman-rank export-offline --out web/public/offline
cd web
npm install
npm run android:sync

if [[ -z "${ANDROID_HOME:-}" && -z "${ANDROID_SDK_ROOT:-}" ]]; then
  echo "Set ANDROID_HOME to your Android SDK, or open the project with:"
  echo "  npx cap open android"
  exit 1
fi

cd android
./gradlew assembleDebug
echo "APK: $root/web/android/app/build/outputs/apk/debug/app-debug.apk"
