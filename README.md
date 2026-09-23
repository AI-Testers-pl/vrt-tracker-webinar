# Screenshot dla AI, decyzja dla człowieka — materiały z webinaru

Materiały z webinaru o Visual Regression Tracker w Playwrighcie: prezentacja, minimalne
demo działające od razu po sklonowaniu oraz skill Claude Code do triażu diffów.

## Zawartość

- [`prezentacja/webinar-vrt-ai.pdf`](prezentacja/webinar-vrt-ai.pdf) — slajdy z webinaru, wyeksportowane do PDF
- [`demo/`](demo/) — mały, samodzielny projekt Playwrighta. Zamiast aplikacji kursowej
  używa jednej statycznej strony (`demo/fixtures/index.html`), więc uruchamia się bez
  żadnych zewnętrznych zależności poza samym trackerem
- [`.claude/skills/vrt-triage/`](.claude/skills/vrt-triage/SKILL.md) — skill do Claude Code:
  pobiera nierozwiązane diffy z trackera, klasyfikuje je (regresja / responsywność / szum)
  i proponuje decyzję (approve / reject)

## Jak odpalić demo

Wymaga Dockera 24+ z Compose v2 oraz Node.js.

```bash
cd demo
npm install
npm run tracker:up          # panel: localhost:8082, API: localhost:4200
```

Zanim cokolwiek puścisz, załóż projekt w panelu (`http://localhost:8082`, logowanie
`visual-regression-tracker@example.com` / `123456`): **New project** → nazwa
`VRT Webinar Demo`. Panel ustawia sensowne wartości porównania obrazów domyślnie —
zakładanie projektu samym wywołaniem API z pustym `imageComparisonConfig` kończy się
cichym `diffPercent: 0` na każdym biegu, bez żadnego błędu.

```bash
npm test          # czysty przebieg, zakłada baseline (status "new" w panelu)
```

Zatwierdź ten wpis w panelu (Approve), żeby stał się baseline'em, a potem:

```bash
npm run test:bug   # ten sam test, z ukrytym logo w headerze
```

Panel pokaże wpis ze statusem `unresolved` i realnym diffem — to jest wejście dla skilla
`vrt-triage`.

## Jak odpalić skill

```
/vrt-triage
```

Skrypt pomocniczy skilla czyta dane logowania ze zmiennych środowiskowych:

```bash
export VRT_EMAIL='visual-regression-tracker@example.com'
export VRT_PASSWORD='123456'
export VRT_APIURL='http://localhost:4200'
export VRT_PROJECT='VRT Webinar Demo'
```

Pełny opis kroków i zasad klasyfikacji jest w
[`SKILL.md`](.claude/skills/vrt-triage/SKILL.md).
