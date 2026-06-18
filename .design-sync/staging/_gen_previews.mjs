// Local-only generator (NOT uploaded). Emits one preview card HTML per Qaren
// category into ui_kits/mobile/, all loading the shared category-driven
// ResultsScreen.jsx. Run: node .design-sync/staging/_gen_previews.mjs
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const outDir = join(here, 'ui_kits', 'mobile');

const TOKENS = `{
      colors: {
        bg: { primary: '#FFFFFF', secondary: '#F8F8FA', inverse: '#0A0A0B' },
        text: { primary: '#0A0A0B', secondary: '#6B7280', placeholder: '#9CA3AF', onInverse: '#FFFFFF' },
        cta: { primary: '#0A0A0B', onPrimary: '#FFFFFF' },
        accent: '#10B981', accentDark: '#059669', accentLight: '#ECFDF5',
        destructive: '#EF4444', warning: '#F59E0B',
        border: { light: '#E5E7EB', medium: '#D1D5DB' }
      },
      spacing: { xs: 4, sm: 8, md: 12, base: 16, lg: 20, xl: 24, '2xl': 32, '3xl': 48 },
      radii: { card: 16, button: 12, chip: 999, input: 12, hero: 24 },
      typography: {}
    }`;

// [key, Label, filename]
const CATS = [
  ['electronics', 'Electronics', 'results.html'],
  ['grocery', 'Grocery', 'results-grocery.html'],
  ['supplements', 'Supplements', 'results-supplements.html'],
  ['makeup', 'Makeup', 'results-makeup.html'],
  ['skincare', 'Skincare', 'results-skincare.html'],
  ['haircare', 'Haircare', 'results-haircare.html'],
  ['fragrances', 'Fragrances', 'results-fragrances.html'],
  ['fashion', 'Fashion', 'results-fashion.html'],
  ['other', 'Other', 'results-other.html'],
];

const tpl = (key, label) => `<!doctype html>
<!-- @dsCard group="UI Kit — Mobile" name="Results — ${label}" subtitle="${label} · verdict · runner-up · dimension bars · at a glance · specs" viewport="540x880" -->
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Qaren — Results · ${label} (card preview)</title>
<link rel="stylesheet" href="../../colors_and_type.css" />
<style>
  html, body { margin: 0; min-height: 100vh; background: #EFEFF3; font-family: var(--qaren-font-en); }
  #root { min-height: 100vh; display: grid; place-items: center; padding: 24px; }
</style>
</head>
<body>
  <div id="root"></div>
  <script>window.qarenTokens = ${TOKENS};</script>
  <script src="https://unpkg.com/react@18.3.1/umd/react.development.js" integrity="sha384-hD6/rw4ppMLGNu3tX5cjIb+uRZ7UkRJ6BPkLpg4hAu/6onKUg4lLsHAs9EBPT82L" crossorigin="anonymous"></script>
  <script src="https://unpkg.com/react-dom@18.3.1/umd/react-dom.development.js" integrity="sha384-u6aeetuaXnQ38mYT8rp6sbXaQe3NL9t+IBXmnYxwkUI2Hw4bsp2Wvmx4yRQF1uAm" crossorigin="anonymous"></script>
  <script src="https://unpkg.com/@babel/standalone@7.29.0/babel.min.js" integrity="sha384-m08KidiNqLdpJqLq95G/LEi8Qvjl/xUYll3QILypMoQ65QorJ9Lvtp2RXYGBFj1y" crossorigin="anonymous"></script>
  <script type="text/babel" src="ios-frame.jsx"></script>
  <script type="text/babel" src="ResultsScreen.jsx"></script>
  <script type="text/babel" data-presets="env,react">
    ReactDOM.createRoot(document.getElementById('root')).render(
      <IOSDevice width={390} height={844}><QarenResultsScreen category="${key}" /></IOSDevice>
    );
  </script>
</body>
</html>
`;

for (const [key, label, file] of CATS) {
  writeFileSync(join(outDir, file), tpl(key, label), 'utf8');
  console.log('wrote', file);
}
