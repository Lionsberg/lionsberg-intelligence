---
title: The phone door speaks TLS
description: How the phone door is reached securely: its two addresses, its certificates, and what trusting them means.
---

# The phone door speaks TLS

This page governs one thing about the phone: how its door is reached securely, through two addresses and certificates the phone trusts. On that, it takes precedence over [DESIGN-DOCK.md](DESIGN-DOCK.md) §4. Everything else about the phone (pairing, the device token, the proxy on loopback, voice notes, sleep) stays with DESIGN-DOCK §4. The code lives in [serve.py](serve.py) (`PhoneDoor`, `PhoneTLSServer`, `PhoneTrustHandler`; its header sections THE PHONE DOOR and THE LAYERED VOICE), [phone_cert.py](phone_cert.py) and [phone-trust.html](phone-trust.html). Related: DESIGN-DOCK §7 (voice), §8.3 (the phone binding) and §8.4 (the security rules); [DESIGN-WAY-IN.md](DESIGN-WAY-IN.md) §3.5 (the phone as a day-two card); the [voice-mode skill](../skills/voice-mode/SKILL.md).

## 1. The one idea

**A phone's browser gives a page its microphone only when the page is secure, so the phone door speaks TLS, with a certificate this computer makes for itself and the phone trusts once.**

- `getUserMedia` (the live microphone) and speech recognition in the browser are given only to a secure context: a page served over https, or from localhost. The phone door is reached at a private-network address, so over plain http Safari on an iPhone and Chrome on Android refuse both. The file picker's recorder (DESIGN-DOCK §4.2) works without it; the loop of speaking and listening does not.
- No public authority will vouch for a private address, and the door must work with no service beyond the person's own computer and phone. So the computer is its own authority, for its own door only, and the phone is asked once to trust it.

## 2. Two addresses, one door

When the person opens the door from this computer's HUD, `serve.py` opens two listeners, both on the one private-network address it already chose (DESIGN-DOCK §8.4: never every address, never a public one):

| Address | Speaks | Serves |
|---|---|---|
| `https://<address>:<phone port>/` | TLS 1.2 or newer (Python's `ssl`) | the door: the HUD, the device token, `/state`, the voice routes, everything DESIGN-DOCK §4 names |
| `http://<address>:<phone port + 1>/` | plain http | **the trust page only**: `GET /` (how to trust this computer, with the fingerprint) and `GET /phone-door.crt` (this computer's authority, DER). Every other request is refused with one sentence naming the https address. |

The plain address is a doorstep: it never serves the HUD, a token, a state or a route that hears. `/phone/pair` answers with the doorstep's address and the code (`address`, so a first-time phone lands on the trust page), the door's own address (`door`) and the fingerprint.

## 3. The certificates

Made by `hud/phone_cert.py` with the Python standard library alone (RSA-2048 keys from Miller-Rabin primes, PKCS#1 v1.5 signatures with SHA-256, the certificate written in DER by hand), so the same code runs on a Mac, on Linux and on Windows, where no `openssl` program can be assumed.

- **The authority** (`ca.key`, `ca.pem`, `ca.crt`): named "Phone door at <address>"; a certificate authority with no authority beneath it; **name constraints** permitting exactly one IP address (the door's, as /32) and DNS names only under `invalid` (a name that never resolves); lives **one year**.
- **The door's certificate** (`door.key`, `door.pem` with the authority after it): the address as its one alternative name, for TLS servers only; lives **thirty days**.
- **Where they live:** `<HQ>/.phone-door/<address>/`, files 0600, folders 0700, named in the kit's [.gitignore](../.gitignore), never in `record/`, never in a cell's clone. One folder per address, so a laptop that moves between two networks keeps both, and a phone that trusted one keeps working there.
- **Renewal:** the door's certificate is renewed quietly a week before its end (checked when the door opens and every six hours while it is open; new connections take the new one). The authority is renewed two weeks before its year ends; that changes the fingerprint, and the HUD says so (§6).

## 4. The trust path, in words

1. On the computer: open the door; the HUD shows the doorstep's address with a pairing code, and the fingerprint.
2. On the phone: open that address. The page says why, shows the same fingerprint, and offers **Get this computer's certificate**.
3. **iPhone or iPad:** tap it, Allow ("Profile Downloaded"); Settings › General › VPN & Device Management › *Phone door at <address>* › Install (its details show the SHA-256 fingerprint to compare); then Settings › General › About › Certificate Trust Settings › full trust for *Phone door at <address>*.
4. **Android:** tap it (the file goes to downloads); Settings › Security & privacy › More security settings › Encryption & credentials › Install a certificate › CA certificate (names differ by maker; search Settings for "CA certificate"); Install anyway; pick the file.
5. Back on the trust page: **Open the door**, which carries the pairing code to the https address. From then on, the https address is the way in.

## 5. What trusting the authority means (said plainly, on the page and here)

- **What it allows:** the phone accepts this computer's door, at that one address, as secure; the browser then lets the door's page use the microphone.
- **What it is made not to allow:** vouching for any other address or any name: not a bank, not a shop, not a website. The limit is written inside the certificate (its name constraints). Safari and Chrome check name constraints; an older or unusual verifier might not, and then the limit rests on the next point alone.
- **Where the risk is:** the authority's key is a file on this computer (0600, in the home, never sent anywhere). Anyone who could copy it could, until it ends, pose as a server at that address to a phone that trusts it. That is the same trust the person already gives this computer; the certificate adds no reach beyond it.
- **How long:** a year at most; a new authority means a new fingerprint and a new trust, never a silent one.
- **How to remove it:** iPhone: Settings › General › VPN & Device Management › the phone door › Remove Profile. Android: Encryption & credentials › User credentials (or Trusted credentials › User) › the phone door › Remove. Letting a phone go in the HUD (DESIGN-DOCK §4.1) revokes its token; removing the certificate is the phone's own act.

## 6. What the HUD shows

`GET /state` carries, in `hud.phone`: `door` (the https address), `trust_page` (the plain one), and `trust`: `{fingerprint, ca_expires, leaf_expires, changed}`, where `changed` is `{was, now, at}` once the authority was renewed while this server ran. The sheet that opens the door shows:

- beside the address, **the fingerprint**, in the figures face, under the words "Compare these figures on your phone";
- when `changed` is set, one line above it: **"This computer's certificate was renewed. Each phone trusts it again, once: open the address below on the phone."**

## 7. The rules

1. The door binds only the private-network address it chose, both listeners; never 0.0.0.0, never a public address, never a new interface.
2. The plain listener serves the trust page and the authority's certificate and refuses everything else, the routes that hear first.
3. No key, certificate or code leaves the computer except the authority's public certificate, to a phone that asks for it on the doorstep.
4. Standard library only; nothing is fetched from the network to make or renew a certificate.
5. A changed fingerprint is always said; the phone is never asked to trust silently.

## 8. How the door is checked

Tests in [engine/tests/test_serve.py](../engine/tests/test_serve.py) (class `PhoneDoorTLS`) check that: the doorstep serves the page and a certificate whose SHA-256 is the fingerprint, and refuses `/voice`, `/voice/say`, `/voice/info`, `/state`, `/stream`, `/phone/claim`, the HUD's files and `/token` in one sentence; TLS serves, is refused by a client that has not trusted the authority, and names the bound address; the files are 0600 and ignored by git; the door's certificate renews alone, and the authority's renewal changes the fingerprint and keeps the one before.

By hand, on a real iPhone and a real Android phone: the trust path of §4 end to end, and the microphone given on the https page. Not yet done: this check by hand has not been run.

## 9. Open

1. Whether an iPhone should be offered a configuration profile (`.mobileconfig`) instead of a bare certificate; it names the door more clearly, at the cost of a second file to make.
2. Whether the doorstep's address should also show as a code for the phone's camera on the computer's sheet.
