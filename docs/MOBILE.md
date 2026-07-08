# Mobile (iOS/Android) via Capacitor

## Overview

Kundali can be packaged as a native iOS and Android app using [Capacitor](https://capacitorjs.com/), which wraps the deployed Next.js web app. This approach:

- **Reuses the web codebase** — no separate native code needed for core features
- **Installers from App Store / Play Store** — users download and install like any native app
- **Progressive enhancement** — PWA (install-to-homescreen) works immediately; Capacitor adds native shells for stores
- **Deferred native features** — push notifications (FCM/APNs) and offline-first data sync can be added later

## When Capacitor (vs. React Native)

Use Capacitor here because:
- App is server-rendered Next.js with full backend (not a client-heavy SPA)
- Web deployment is the primary surface; mobile is an add-on
- Smaller team → single codebase is force multiplier
- PWA already solves install-to-homescreen (freemium users happy)
- Native features (notifications, sensor access) added incrementally as RFCs

React Native makes sense for mobile-first, offline-heavy apps; not this case.

## Quickstart

### Prerequisites

```bash
node -v  # 18+
npm -v   # 9+
xcode-select --install  # macOS: Xcode command-line tools
brew install android-studio  # Android SDK (or use Android Studio GUI)
```

### 1. Initialize Capacitor

```bash
npm install @capacitor/core @capacitor/cli
npx cap init kundali com.technektar.kundali --web-dir=out
```

**Output:** Creates `capacitor.config.json` with app ID `com.technektar.kundali`.

### 2. Choose Deployment Strategy

#### Option A: Remote Web App (Recommended for MVP)

Point Capacitor at the production web server. Users always get the latest version from the deployed URL.

In `capacitor.config.json`:

```json
{
  "appId": "com.technektar.kundali",
  "appName": "Kundali",
  "webDir": "out",
  "server": {
    "url": "https://kundali.example.com",
    "cleartext": false
  }
}
```

**Pros:**
- Single deploy pipeline (web only)
- Instant bug fixes
- No app review delays for web changes

**Cons:**
- Requires network connectivity
- App Store policies: may require disclosure that app is web-wrapped

#### Option B: Static Export (More Offline)

Build Next.js as static (`output: 'export'`), bundle in app.

In `next.config.mjs`:

```javascript
export default {
  output: 'export',
  // ... rest of config
};
```

Then:

```bash
npm run build  # Outputs to `out/`
npx cap add ios
npx cap add android
npx cap build ios  # Builds Xcode project
npx cap build android  # Builds Android Studio project
```

**Pros:**
- Works offline
- Faster load (no network latency)

**Cons:**
- App Store review process (weeks)
- Must rebuild + resubmit for every content change

### 3. Add Native Platforms

```bash
npx cap add ios
npx cap add android
```

Creates `ios/` and `android/` folders with native projects.

### 4. Development Loop

#### iOS

```bash
npx cap sync ios  # Sync web changes to Xcode project
npx cap open ios  # Open Xcode
# In Xcode: Product > Run, or set up device / simulator
```

#### Android

```bash
npx cap sync android  # Sync web changes to Android Studio
npx cap open android  # Open Android Studio
# In Android Studio: Run / Debug configuration, select emulator or device
```

## Code Signing & Store Submission

### iOS (App Store)

1. **Create Apple Developer account** (~$99/year)
2. **Generate provisioning profiles** in Apple Developer portal
3. **In Xcode:**
   - Set Team ID (Signing & Capabilities tab)
   - Set Bundle ID to match (`com.technektar.kundali`)
   - Archive (Product > Archive)
   - Upload to App Store Connect
4. **App Store review** (typically 24–48h; web-wrapped apps may take longer)

### Android (Play Store)

1. **Create Google Play Developer account** (~$25 one-time)
2. **Generate signing key:**

```bash
keytool -genkey -v -keystore kundali.keystore -keyalg RSA -keysize 2048 -validity 10000 -alias kundali
```

3. **In Android Studio:**
   - Build > Generate Signed Bundle/APK
   - Select "APK" or "Bundle"
   - Choose keystore, select alias
4. **Upload to Google Play Console**
5. **Publish** (approval typically 2–4h; can be instant for updates)

## Testing Pre-Submission

```bash
# Test on iOS simulator
npx cap open ios  # Xcode → select iPhone 15 Pro → Run

# Test on Android emulator
npx cap open android  # Android Studio → select emulator → Run

# Or on real devices via USB with developer mode enabled
```

## What to Revisit Later

### Push Notifications

Add Firebase Cloud Messaging (FCM) and Apple Push Notification service (APNs):

```bash
npm install @capacitor/push-notifications
npx cap sync
```

Then:
- Wire up FCM credentials to Firebase console
- Register device tokens in Supabase
- Send pushes from backend RPC

### Offline Data Sync

Add local database + background sync:

```bash
npm install @capacitor/storage @capacitor/network
# Or use WatermelonDB, Realm, SQLite plugin
```

Persist reads locally; queue writes; sync on network restore.

### Deep Linking

Enable app-to-app navigation:

```json
{
  "plugins": {
    "capacitor-community/fcm": {},
    "@capacitor/deep-links": {
      "scheme": "kundali",
      "host": "app"
    }
  }
}
```

### Biometric Auth

```bash
npm install @capacitor-community/biometric
```

Replace password entry with fingerprint/Face ID on supported devices.

## Monitoring

After launch:

- **Crash logs:** Enable Firebase Crashlytics in Capacitor config
- **Analytics:** Segment, Mixpanel, or Amplitude SDKs work in Capacitor
- **App Store Optimization:** Monitor star ratings, update frequency based on feedback

## Resources

- [Capacitor docs](https://capacitorjs.com/docs)
- [Apple App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) (watch for web-wrapped disclosure rules)
- [Google Play Policies](https://play.google.com/about/developer-content-policy/)
- [Capacitor Plugins Registry](https://capacitorjs.com/plugins)

---

**Version:** 1.0 · Kundali MVP
