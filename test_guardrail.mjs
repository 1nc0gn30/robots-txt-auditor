import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

const MIME_TYPES = {
  '.html': 'text/html; charset=UTF-8',
  '.css': 'text/css; charset=UTF-8',
  '.js': 'text/javascript; charset=UTF-8',
  '.json': 'application/json; charset=UTF-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.txt': 'text/plain; charset=UTF-8',
  '.xml': 'application/xml; charset=UTF-8'
};

const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];
  if (reqPath === '/') reqPath = '/index.html';
  if (reqPath.endsWith('/')) reqPath += 'index.html';

  let filePath = path.join(process.cwd(), 'public', reqPath);
  if (!fs.existsSync(filePath) && fs.existsSync(filePath + '.html')) {
    filePath += '.html';
  }

  if (!fs.existsSync(filePath)) {
    filePath = path.join(process.cwd(), 'public', 'index.html');
  }

  const ext = path.extname(filePath);
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(500);
      res.end('Error');
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content);
    }
  });
});

const PORT = 4280 + Math.floor(Math.random() * 200);
server.listen(PORT, async () => {
  console.log(`Test server running at http://127.0.0.1:${PORT}`);
  
  const CHROME = '/usr/bin/google-chrome';
  const CDP_PORT = 9422;
  const chrome = spawn(CHROME, [
    '--headless=new',
    `--remote-debugging-port=${CDP_PORT}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--autoplay-policy=no-user-gesture-required',
    '--mute-audio',
    '--renderer-process-limit=2',
    `--user-data-dir=/tmp/guardrail-cdp-${CDP_PORT}`,
    'about:blank',
  ], { stdio: 'ignore' });

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  let ws;
  let seq = 0;
  const pending = new Map();
  let errors = [];

  try {
    for (let i = 0; i < 60 && !ws; i++) {
      try {
        const list = await (await fetch(`http://127.0.0.1:${CDP_PORT}/json`)).json();
        const page = list.find((t) => t.type === 'page');
        if (page) ws = new WebSocket(page.webSocketDebuggerUrl);
      } catch { /* waiting */ }
      if (!ws) await sleep(200);
    }
    if (!ws) throw new Error('Chrome target not found');

    await new Promise((r) => ws.addEventListener('open', r));

    ws.addEventListener('message', (e) => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
      if (m.method === 'Runtime.exceptionThrown') {
        const d = m.params.exceptionDetails;
        errors.push(d.exception?.description || d.text);
      }
      if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
        errors.push(m.params.args.map((a) => a.value ?? a.description).join(' '));
      }
    });

    const send = (method, params = {}) => new Promise((r) => {
      const id = ++seq; pending.set(id, r); ws.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async (expression) =>
      (await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })).result?.result?.value;

    await send('Runtime.enable');
    await send('Page.enable');
    await send('Network.enable');

    const viewports = [
      { name: 'mobile', width: 375, height: 812, mobile: true },
      { name: 'tablet', width: 768, height: 1024, mobile: true },
      { name: 'desktop', width: 1440, height: 900, mobile: false }
    ];

    const routes = [
      '/',
      '/cities/norfolk-va/agencies/',
      '/terms.html',
      '/privacy.html',
      '/support.html'
    ];

    let hasFailure = false;

    for (const route of routes) {
      console.log(`\nTesting route: ${route}`);
      for (const vp of viewports) {
        await send('Emulation.setDeviceMetricsOverride', {
          width: vp.width,
          height: vp.height,
          deviceScaleFactor: 1,
          mobile: vp.mobile
        });
        errors = [];
        await send('Page.navigate', { url: `http://127.0.0.1:${PORT}${route}` });
        await sleep(1000);

        const metrics = await evaluate(`({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          bodyScrollWidth: document.body.scrollWidth,
          bodyClientWidth: document.body.clientWidth,
          overflowPx: Math.max(
            document.documentElement.scrollWidth - document.documentElement.clientWidth,
            document.body.scrollWidth - document.body.clientWidth
          ),
          imgsMissingAlt: [...document.images].filter(i => !i.hasAttribute('alt') || !i.alt.trim()).length,
          buttons: document.querySelectorAll('button, [role=button], a[href]').length,
          textLength: (document.body.innerText || '').trim().length
        })`);

        const isOverflow = metrics.overflowPx > 0;
        console.log(`  [${vp.name} ${vp.width}x${vp.height}] overflow: ${metrics.overflowPx}px | buttons: ${metrics.buttons} | text: ${metrics.textLength} | missingAlt: ${metrics.imgsMissingAlt}`);

        if (isOverflow) {
          console.error(`  ❌ Horizontal overflow detected on ${route} at ${vp.name}!`);
          hasFailure = true;
        }
        if (metrics.imgsMissingAlt > 0) {
          console.error(`  ❌ Missing alt text detected on ${route}! Count: ${metrics.imgsMissingAlt}`);
          hasFailure = true;
        }
        if (errors.length > 0) {
          console.error(`  ❌ Console errors on ${route} at ${vp.name}:`, errors);
          hasFailure = true;
        }
      }
    }

    if (hasFailure) {
      console.error('\n❌ Guardrail check failed.');
      process.exitCode = 1;
    } else {
      console.log('\n✅ 7-point guardrail verification passed across all routes & viewports!');
      process.exitCode = 0;
    }
  } catch (err) {
    console.error('Test run failed with error:', err);
    process.exitCode = 1;
  } finally {
    try { ws?.close(); } catch {}
    chrome.kill('SIGKILL');
    server.close();
  }
});
