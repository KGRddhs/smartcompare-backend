/**
 * Render Claude-Design reference HTML mounts → PNG screenshots.
 *
 * Each per-screen .html mounts a single Qaren screen inside an IOSDevice
 * frame (390×844). We open each in Chromium, wait for the JSX/Babel
 * runtime to transform + mount the React tree under #root, then capture
 * at retina (deviceScaleFactor=2).
 *
 * Output: ../screenshots/<name>.png (e.g. home.png, results.png).
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const MOBILE_DIR = path.resolve(__dirname, 'ui_kits/mobile');
const OUT_DIR = path.resolve(__dirname, 'screenshots');

// Skip non-mount-point HTML or non-per-screen demos.
const SKIP = new Set(['index.html']); // multi-screen demo, we screenshot the per-screen pages instead

async function main() {
  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

  const files = fs.readdirSync(MOBILE_DIR)
    .filter(f => f.endsWith('.html') && !SKIP.has(f))
    .sort();

  console.log(`Rendering ${files.length} screens to ${OUT_DIR}`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 460, height: 920 },
    deviceScaleFactor: 2,
  });

  let ok = 0, fail = 0;
  for (const file of files) {
    const url = `http://127.0.0.1:8731/ui_kits/mobile/${file}`;
    const name = file.replace(/\.html$/, '');
    const outPath = path.join(OUT_DIR, `${name}.png`);
    const page = await context.newPage();
    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });

      // Babel transforms type="text/babel" scripts asynchronously after page
      // load. Wait for the React tree to mount under #root.
      await page.waitForFunction(
        () => {
          const root = document.getElementById('root');
          return root && root.children.length > 0 && root.querySelector('div, section, header, main');
        },
        { timeout: 20000 }
      );

      // Settle any opening animations (concentric rings, counter ticks, etc).
      await page.waitForTimeout(1800);

      await page.screenshot({ path: outPath, fullPage: false });
      console.log(`  ✓ ${name}.png`);
      ok++;
    } catch (err) {
      console.log(`  ✗ ${name}.png — ${err.message.split('\n')[0]}`);
      fail++;
    } finally {
      await page.close();
    }
  }

  await browser.close();
  console.log(`\nDone — ${ok} ok, ${fail} failed`);
  process.exit(fail > 0 ? 1 : 0);
}

main().catch(e => { console.error(e); process.exit(2); });
