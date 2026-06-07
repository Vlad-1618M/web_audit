# Developer ID signing & notarization (public DMG)

One-time setup (already on your Mac if `security find-identity` shows **1 valid identity**):

- Apple Developer Program + **Developer ID Application** cert in Keychain
- Apple intermediate certs (G2 + WWDR G3) if needed
- `xcrun notarytool store-credentials "webaudit-notarize" …`

## Every release

```bash
cd macos

# Unsigned DMG (beta / CI)
./orchestrate-macos.sh public-dmg

# Signed DMG (local; requires Developer ID)
./orchestrate-macos.sh public-signed-dmg

# Signed + notarized + stapled DMG (ship to users)
./orchestrate-macos.sh public-notarize
```

Or step-by-step from `packaging/public-installer/`:

| Script | What |
|--------|------|
| `build-app.sh` | Unsigned `.app` |
| `../_shared/sign-app-bundle.sh` | Sign Engine + Playwright + `WebAuditMac` |
| `make-dmg.sh` | DMG from staged app |
| `build-signed-dmg.sh` | build + sign + DMG |
| `notarize-release.sh` | notarize app → staple → DMG → notarize DMG |

## Environment

| Variable | Default |
|----------|---------|
| `SIGN_ID` | Auto: first `Developer ID Application` in Keychain |
| `NOTARY_PROFILE` | `webaudit-notarize` |
| `ENTITLEMENTS` | `entitlements.plist` in this directory |

## Troubleshooting

```bash
security find-identity -v -p codesigning
xcrun notarytool history --keychain-profile webaudit-notarize
xcrun notarytool log <submission-id> --keychain-profile webaudit-notarize
codesign --verify --deep --strict --verbose=2 "build/Web Audit.app"
```

Personal checklist copy: `~/webaudit-release-tools/MAC_SIGNING_MEMO.txt`
