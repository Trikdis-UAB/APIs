# Įgyvendinimo planas: IPcom API dokumentacijos apsauga su Cloudflare Access

## Santrauka
Tikslas: perkelti IPcom API dokumentaciją iš viešai pasiekiamo modelio į `identity-based access` modelį, naudojant Cloudflare Access prieš VPS hostinamą statinę dokumentaciją.
Sprendimas leidžia išlaikyti privatų GitHub repo, tęsti CI/CD per GitHub Actions ir valdyti partnerių prieigą centralizuotai per Cloudflare.

## Užfiksuoti sprendimai (decision lock)
1. DNS modelis: **pilnas zonos perkėlimas į Cloudflare** (`trikdis.com` authoritative nameservers Cloudflare).
2. Prisijungimas: **abu metodai** - Google SSO ir Email OTP.
3. Onboarding: **invite-only** (viešos registracijos nėra).
4. Dokumentacija lieka hostinama VPS; Cloudflare veikia kaip prieigos ir edge apsaugos sluoksnis.
5. Authentik šiame etape nenaudojamas.

## Viešų sąsajų / interface pokyčiai
1. `https://api.docs.trikdis.com` tampa auth-reikalaujamu endpointu (nebe viešas).
2. Prisijungimo langą pateikia Cloudflare Access (redirect į Access login UI).
3. Partnerių prieiga valdoma per Cloudflare Access politikas ir allowlist/grupes.
4. IPcom receiver API (`/api/*`) kontraktai ir funkcionalumas nesikeičia.

## Architektūra ir srautas
1. `User -> Cloudflare Edge -> Cloudflare Access policy check -> VPS static docs`.
2. Jei vartotojas neautentifikuotas ar neleistinas, Cloudflare blokuoja iki origin.
3. Origin (VPS) nebeturi savos auth logikos dokumentacijai.
4. GitHub Actions deployina statinius failus į VPS (`/srv/ipcom-docs/current`).

## Reikalingi komponentai
1. Cloudflare zona `trikdis.com`.
2. Cloudflare Zero Trust tenantas.
3. Access Application tipas: `Self-hosted` (`api.docs.trikdis.com`).
4. IdP:
   - Google (primary SSO).
   - One-Time PIN (OTP) fallback.
5. VPS su statiniu docs hostingu.
6. GitHub Actions deploy pipeline.

## DNS ir platformos nustatymai
### DNS įrašai
| Host | Tipas | Reikšmė | TTL |
|---|---|---|---|
| `api.docs.trikdis.com` | `A` | `<VPS_PUBLIC_IP>` | `300` |
| `docs-origin.trikdis.com` (nebūtina, ops) | `A` | `<VPS_PUBLIC_IP>` | `300` |

### TLS ir tinklas
1. Cloudflare proxy (`orange cloud`) įjungtas `api.docs.trikdis.com`.
2. SSL/TLS mode: `Full (strict)` (origin turi valid cert).
3. VPS firewall: leisti `80/443`, SSH riboti admin IP.
4. Origin web server turi priimti tik Cloudflare srautą (allowlist Cloudflare IP ranges + admin SSH).

## Cloudflare Access politika (invite-only su Google + OTP)
1. **Default deny** visiems, kurie neatitinka allow taisyklių.
2. Sukurti Access list/grupę `docs_partners_allowlist` su konkrečiais partnerių email.
3. `Allow policy`:
   - `Emails in docs_partners_allowlist`
   - Login methods: Google ir OTP.
4. `Admin policy`:
   - atskira `docs_admins_allowlist` arba Google admin grupė.
5. Session TTL:
   - Partneriams: 8h.
   - Adminams: 4h.
6. Revoke procesas:
   - pašalinti iš allowlist.
   - priverstinai nutraukti aktyvias sesijas (`Team & Resources > Users > Revoke`).

## Svarbi pastaba dėl Google + OTP
1. OTP atveju IdP grupės claim'ai nenaudojami taip, kaip Google SSO flow.
2. Todėl invite-only turi remtis **explicit email allowlist**, ne vien Google grupėmis.
3. Jei ateityje norėsis strict enterprise lifecycle, pereiti į `Google-only + group-based` arba SCIM modelį.

## Įgyvendinimo fazės
## 1 fazė: Cloudflare bazė
1. Sukurti/importuoti `trikdis.com` zoną į Cloudflare.
2. Perjungti registrar nameservers į Cloudflare.
3. Sukonfigūruoti DNS įrašus `api.docs.trikdis.com`.
4. Patikrinti DNS propagaciją ir rollback langą.

## 2 fazė: Origin paruošimas (VPS)
1. Paruošti web serverį statiniams docs.
2. Įdiegti valid origin cert (Cloudflare Origin CA arba viešas cert).
3. Apriboti origin prieigą tik per Cloudflare + admin kanalus.
4. Įjungti access logs.

## 3 fazė: Access konfigūracija
1. Zero Trust: sukurti `Self-hosted app` `api.docs.trikdis.com`.
2. Pridėti Google IdP.
3. Įjungti OTP kaip papildomą login metodą.
4. Sukurti allowlist-based policies.
5. Nustatyti session TTL ir priverstinę re-auth pagal riziką.

## 4 fazė: CI/CD deploy
1. Private repo su docs source.
2. GitHub Actions: build -> artifact -> deploy į VPS.
3. Atomic deploy per release katalogus ir symlink switch.
4. Rollback skriptas į ankstesnį release.

## 5 fazė: Operaciniai procesai
1. Onboarding SOP: kas kviečia, kas tvirtina, koks SLA.
2. Offboarding SOP: allowlist remove + session revoke.
3. Audit SOP: mėnesinė vartotojų peržiūra.
4. Incident SOP: laikinas global deny, partnerių whitelist restore.

## Testai ir scenarijai
1. Anonymous vartotojas atidaro `api.docs.trikdis.com` -> mato Access login.
2. Leistinas partneris su Google SSO prisijungia -> docs pasiekiami.
3. Leistinas partneris su OTP prisijungia -> docs pasiekiami.
4. Neleistinas email su Google/OTP -> prieiga atmetama.
5. Pašalintas vartotojas po session revoke -> nebegali tęsti sesijos.
6. Admin vartotojas turi atskirą policy ir trumpesnį TTL.
7. Origin URL tiesiogiai (apeinant Cloudflare) nepasiekiamas.
8. GitHub Actions deploy atnaujina docs be downtime.
9. Rollback grąžina ankstesnę versiją.
10. Access audit log'ai fiksuoja loginus ir denied bandymus.

## Priėmimo kriterijai
1. Dokumentacija nepasiekiama neautentifikuotiems vartotojams.
2. Invite-only veikia su explicit allowlist.
3. Grant/revoke atliekamas be serverio perkrovimo.
4. Aktyvi sesija gali būti nutraukiama administratoriaus.
5. CI/CD deploy į VPS veikia iš private repo.
6. Origin nėra viešai apeinamas tiesioginiu IP/host keliu.

## Rollout planas
1. Savaitė 1: DNS migracija į Cloudflare, origin hardening, Access app sukūrimas.
2. Savaitė 2: pilotas su vidiniais vartotojais ir 1-2 partneriais.
3. Savaitė 3: pilna partnerių migracija, seno viešo endpoint uždarymas/redirect.

## Stebėsena ir audit
1. Cloudflare Access logs įjungti ir saugoti.
2. Alertai:
   - daug failed login per trumpą laiką,
   - denied spike,
   - netikėti admin login.
3. Mėnesinė allowlist ir admin teisių peržiūra.

## Rizikos ir mitigacija
1. DNS migracijos rizika -> planuotas maintenance langas + rollback planas.
2. Klaidinga policy gali užblokuoti visus -> turėti bent 2 break-glass admin paskyras.
3. OTP gali būti silpnesnis lifecycle prasme -> remtis explicit allowlist ir periodiniu auditu.
4. Origin bypass rizika -> firewall + Cloudflare-only origin access.

## Prielaidos ir numatytos reikšmės
1. Komanda gali perkelti `trikdis.com` DNS į Cloudflare.
2. Partnerių modelis lieka invite-only.
3. Naudojami abu login metodai: Google SSO + OTP.
4. Dokumentacijos hostinimas lieka VPS.
5. Authentik šiame etape neįtraukiamas.
