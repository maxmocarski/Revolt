// Browser checks for the ReVolt UI at iPhone size, using headless Chrome and canned scan results
// (no AI model needed). Start the app first, then from the repo root:
//
//   node tests/ui/run_ui_tests.mjs [http://127.0.0.1:8502]
//
// Needs Node 22+ and Google Chrome (set CHROME_PATH if it isn't in the default macOS location).
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const BASE = process.argv[2] || 'http://127.0.0.1:8502';
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9400 + Math.floor(Math.random() * 500);
const here = path.dirname(fileURLToPath(import.meta.url));
const fixtures = fs.readFileSync(path.join(here, 'fixtures.json'), 'utf8');
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'revolt-ui-'));
const shotsDir = process.env.SHOTS_DIR;   // optional: save screenshots here

const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let target;
for (let i = 0; i < 75 && !target; i++) {
  await sleep(200);
  try { target = (await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()).find(t => t.type === 'page'); } catch {}
}
if (!target) { console.error('Could not start Chrome at', CHROME); chrome.kill(); process.exit(2); }

const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let id = 0;
const pending = {};
const pageErrors = [];
ws.onmessage = m => {
  const d = JSON.parse(m.data);
  if (d.method === 'Runtime.exceptionThrown') pageErrors.push(d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text);
  pending[d.id]?.(d.result ?? d);
};
const cmd = (method, params = {}) => new Promise(r => { pending[++id] = r; ws.send(JSON.stringify({ id, method, params })); });
const ev = async expr => {
  const r = await cmd('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 300));
  return r.result?.value;
};
const shot = async name => {
  if (!shotsDir) return;
  fs.writeFileSync(path.join(shotsDir, `${name}.png`), Buffer.from((await cmd('Page.captureScreenshot', { format: 'png' })).data, 'base64'));
};
const center = sel => ev(`(() => { const r = document.querySelector(${JSON.stringify(sel)}).getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
const tap = async sel => {
  const { x, y } = await center(sel);
  await cmd('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
  await cmd('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await sleep(450);
};
const drag = async (sel, dy) => {
  const { x, y } = await center(sel);
  await cmd('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
  for (let i = 1; i <= 8; i++) { await cmd('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x, y: y + dy * i / 8 }] }); await sleep(16); }
  await cmd('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await sleep(500);
};
const key = async (k, shift = false) => {
  const code = k === 'Escape' ? 27 : 9;
  for (const type of ['keyDown', 'keyUp']) await cmd('Input.dispatchKeyEvent', { type, key: k, code: k, windowsVirtualKeyCode: code, modifiers: shift ? 8 : 0 });
  await sleep(150);
};
let failures = 0;
const check = (label, pass, detail = '') => {
  if (!pass) failures++;
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${label}${detail ? '  ' + detail : ''}`);
};
const scanFixture = async (fx, delay = 300) => {
  await ev(`nextScan = { fx: '${fx}', delay: ${delay} }; scanAnother(); 1`);
  await sleep(400);
  await tap('#shutterBtn');
  await sleep(delay + 600);
};

try {
  await cmd('Runtime.enable');
  await cmd('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
  await cmd('Emulation.setTouchEmulationEnabled', { enabled: true });
  await cmd('Page.navigate', { url: BASE + '/' });
  await sleep(1500);

  // Serve canned results for /api/scan* so checks don't depend on the AI model.
  await ev(`window.FX = ${fixtures}; window.nextScan = { fx: 'laptop', delay: 300 };
    const realFetch = window.fetch;
    window.fetch = (url, opts = {}) => {
      if (!String(url).startsWith('/api/scan')) return realFetch(url, opts);
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => resolve(new Response(JSON.stringify(FX[nextScan.fx]), { status: 200, headers: { 'Content-Type': 'application/json' } })), nextScan.delay);
        if (opts.signal) opts.signal.addEventListener('abort', () => { clearTimeout(timer); reject(new DOMException('aborted', 'AbortError')); });
      });
    }; 1`);

  // Landing page
  check('viewport allows pinch-zoom', !(await ev(`document.querySelector('meta[name=viewport]').content`)).includes('user-scalable=no'));
  check('every button has an accessible name', (await ev(`[...document.querySelectorAll('button')].filter(b => !(b.getAttribute('aria-label') || b.textContent.trim())).length`)) === 0);
  check('no third-party stylesheets or scripts', (await ev(`[...document.querySelectorAll('link[rel=stylesheet], script[src]')].filter(e => new URL(e.href || e.src).origin !== location.origin).length`)) === 0);
  await ev(`document.fonts.ready.then(() => 1)`);
  check('self-hosted icon font loaded', await ev(`document.fonts.check('900 16px "Font Awesome 6 Free"')`));
  check('first visit shows how-it-works steps, not stats', await ev(`!landingSteps.hidden && landingStatsBlock.hidden`));
  await shot('01_landing');

  await tap('#startScanBtn');
  await sleep(800);
  check('camera starts only after Start Scanning', await ev(`!!cameraStream`));

  // Verdicts and labels
  await tap('#shutterBtn');
  await sleep(900);
  const laptop = await ev(`({ verdict: document.querySelector('.verdict')?.className, levels: [...document.querySelectorAll('.card:not(.dashed) .result-list li')].map(li => li.className) })`);
  check('laptop: danger verdict, both hazards tagged danger', laptop.verdict === 'verdict danger' && laptop.levels.slice(0, 2).join() === 'danger,danger', JSON.stringify(laptop));
  await shot('02_result_danger');
  await ev(`document.querySelector('details').open = true; 1`);
  check('AI-written specs tagged "AI"', (await ev(`[...document.querySelectorAll('.spec-tag')].map(t => t.textContent)`)).every(t => t === 'AI'));

  // Drawer keeps results
  await tap('#drawerHandle');
  check('tapping the handle collapses but keeps the result', await ev(`!isExpanded && !!document.querySelector('.verdict') && frozenPreview.style.display === 'none'`));
  await tap('.drawer-title');
  check('tapping the collapsed strip reopens the result', await ev(`isExpanded && !!document.querySelector('.verdict')`));
  await drag('#drawerHandle', 350);
  check('dragging the handle down collapses (result kept)', await ev(`!isExpanded && !!document.querySelector('.verdict')`));

  for (const [fx, level] of [['drive', 'privacy'], ['ram', 'safe'], ['printer', 'caution']]) {
    await scanFixture(fx);
    check(`${fx}: ${level} verdict`, (await ev(`document.querySelector('.verdict')?.className`)) === `verdict ${level}`);
    if (fx === 'drive') {
      const tags = await ev(`[...document.querySelectorAll('.spec-tag')].map(t => t.textContent)`);
      check('label-decoded specs tagged "Label"', tags.length > 0 && tags.every(t => t === 'Label'), JSON.stringify(tags));
    }
  }

  // Slow scan + cancel (don't wait for it to finish)
  await ev(`nextScan = { fx: 'laptop', delay: 20000 }; scanAnother(); 1`);
  await sleep(400);
  await tap('#shutterBtn');
  await sleep(8600);
  check('slow scan shows the warming-up hint', /Warming up/.test((await ev(`document.getElementById('loadingHint')?.textContent`)) || ''));
  await tap('.loading-state .btn');
  check('Cancel stops the scan and shows a toast', await ev(`!scanning && !isExpanded && toast.textContent === 'Scan cancelled'`));

  // Flashlight on a camera without one: toast, not alert()
  await tap('#flashToggleBtn');
  check('missing flashlight shows a toast', await ev(`toast.classList.contains('show')`));

  // Dialogs
  await ev(`document.querySelector('.nav-actions button[aria-label="Settings"]').focus(); openModal('settingsModal'); 1`);
  await sleep(200);
  check('opening Settings focuses Close', await ev(`document.activeElement === settingsModal.querySelector('.modal-close-btn')`));
  check('opening a dialog hides any toast', await ev(`!toast.classList.contains('show')`));
  await key('Tab', true);
  check('Shift+Tab stays inside the dialog', await ev(`settingsModal.contains(document.activeElement)`));
  await key('Escape');
  check('Escape closes Settings and returns focus', await ev(`settingsModal.style.display === 'none' && document.activeElement.getAttribute('aria-label') === 'Settings'`));
  await ev(`openModal('settingsModal'); document.querySelector('button.settings-row').click(); 1`);
  await sleep(1200);
  check('Settings → Usage Statistics opens stats', await ev(`analyticsModal.style.display === 'flex' && settingsModal.style.display === 'none'`));
  await key('Escape');

  // Results saved before hazard levels / spec labels existed still render
  await ev(`displayAnalysisResults({ item: 'Old saved scan', hazards: ['Contains a lithium-ion battery: fire risk'], dispose: ['Recycle it'], specs: { Type: 'DDR4' } }); snapDrawer(true); 1`);
  check('old saved results still render', await ev(`!!document.querySelector('.verdict.danger') && document.querySelectorAll('.spec-tag').length === 0`));
  await key('Escape');
  check('Escape collapses the drawer', await ev(`!isExpanded`));

  // Landing stats: 4 successful scans so far (laptop, drive, ram, printer); the cancelled one does not count
  await tap('.brand-badge');
  const stats = await ev(`({ scans: statScans.textContent, hazardous: statHazardous.textContent, kg: statKg.textContent, steps: landingSteps.hidden, cameraOff: !cameraStream })`);
  check('home screen shows stats after scans', stats.scans === '4' && stats.hazardous === '1' && stats.steps && stats.cameraOff, JSON.stringify(stats));
  await shot('03_landing_stats');

  // Small phone
  await cmd('Emulation.setDeviceMetricsOverride', { width: 320, height: 568, deviceScaleFactor: 2, mobile: true });
  await sleep(300);
  check('320×568: Start Scanning visible without scrolling', await ev(`startScanBtn.getBoundingClientRect().bottom <= innerHeight`));
  await tap('#startScanBtn');
  await sleep(600);
  await scanFixture('laptop', 100);
  check('320px wide: no horizontal overflow', await ev(`document.documentElement.scrollWidth <= 320 && drawerContent.scrollWidth <= drawerContent.clientWidth`));

  check('no JavaScript errors', pageErrors.length === 0, pageErrors.join(' | ').slice(0, 300));
} catch (err) {
  failures++;
  console.error('FAIL  test run crashed:', err.message);
} finally {
  ws.close();
  const exited = new Promise(r => chrome.once('exit', r));
  chrome.kill();
  await Promise.race([exited, sleep(3000)]);
  fs.rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
}
console.log(failures ? `\n${failures} check(s) failed` : '\nAll UI checks passed');
process.exit(failures ? 1 : 0);
