# AIOS Capture (watchOS)

Native Brain Dump capture for Apple Watch. Posts to the existing web endpoint:

`POST /capture/submit` with `capture_interface: "watchos_v1"`.

## Architecture

| Piece | Role |
|-------|------|
| `AIOSCaptureCore` (Swift package) | HTTP client, Brain Dump splitting, Keychain settings |
| `WatchApp/` | watchOS SwiftUI source to add to an Xcode target |
| Web `/capture/submit` | Existing AIOS capture path (no backend change required for v1) |

### watch-first (#2) → iPhone companion (#3)

This layout is intentional:

1. **Now:** watch-only app + shared `AIOSCaptureCore` package.
2. **Later:** add an iOS app target to the same Xcode project.
3. **Shared code stays put:** `CaptureClient`, `BrainDumpFormatter`, settings types.
4. **Move setup to iPhone:** sign-in screen on iOS, credentials in a shared Keychain App Group (`KeychainCaptureSettingsStore(accessGroup: "...")`).
5. **Optional:** `WatchConnectivity` to relay captures when the watch is off-LTE or auth is iPhone-only.

You do not rewrite capture logic when adding the companion — you add targets and swap the settings store implementation.

## Create the watch app in Xcode

1. Open Xcode → **File → New → Project**.
2. Choose **watchOS → App**. Name it `AIOS Capture`, organization identifier e.g. `com.yourname.aios`.
3. Save the project inside this folder: `apps/aios-capture/AIOSCapture.xcodeproj` (or adjacent — your choice).
4. **File → Add Package Dependencies → Add Local…** and select this directory (`apps/aios-capture`).
5. Add `AIOSCaptureCore` to the Watch app target.
6. Replace the generated Watch app sources with the files in `WatchApp/`:
   - `AIOSCaptureWatchApp.swift`
   - `CaptureModel.swift`
   - `CaptureView.swift`
7. Watch target → **Signing & Capabilities** → set your Team.
8. Watch target → **Info** → add App Transport Security only if you test against non-HTTPS (production URL is HTTPS).

## First-run setup on the watch

1. Enter the AIOS web URL (default production: `https://aios-web-fcfzjohmmq-nn.a.run.app`).
2. Username: `aios`
3. Password: your AIOS web password (Secret Manager value).
4. Capture with dictation via the standard Watch text field mic.

## Run tests (core package)

From this directory:

```bash
swift test
```

## Future iOS companion (sketch)

When you add #3:

- Create an **iOS App** target in the same project.
- Reuse `AIOSCaptureCore`.
- Add an iOS settings view that writes `CaptureSettings` to a shared Keychain access group.
- Watch app reads the same access group — remove or hide on-watch password entry.
- Optional: complication that opens the capture screen.

## Future backend polish (optional)

v1 uses HTTP Basic Auth against the web app (same as the PWA). For a smoother long-term setup, add a capture-only device token on the server so the watch never stores your main password.
