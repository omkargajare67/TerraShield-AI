import { spawn } from 'child_process';
import http from 'http';

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const PORT = 9222;

async function run() {
  console.log('Launching Edge headless...');
  const edge = spawn(EDGE_PATH, [
    `--remote-debugging-port=${PORT}`,
    '--headless=new',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--user-data-dir=' + process.env.TEMP + '\\edge_test_profile_' + Date.now(),
    'about:blank',
  ], { stdio: 'ignore' });

  // Wait for CDP to be available
  let versionData = null;
  for (let i = 0; i < 20; i++) {
    await new Promise(r => setTimeout(r, 300));
    try {
      versionData = await new Promise((resolve, reject) => {
        http.get(`http://127.0.0.1:${PORT}/json/version`, (res) => {
          let raw = '';
          res.on('data', chunk => raw += chunk);
          res.on('end', () => resolve(JSON.parse(raw)));
        }).on('error', reject);
      });
      if (versionData) break;
    } catch {}
  }

  if (!versionData) {
    console.error('Failed to connect to Edge CDP');
    edge.kill();
    return;
  }

  console.log('Connected to Edge:', versionData.Browser);

  // Create new target via PUT
  const newTarget = await new Promise((resolve, reject) => {
    const req = http.request({
      hostname: '127.0.0.1',
      port: PORT,
      path: '/json/new?http://127.0.0.1:5173',
      method: 'PUT'
    }, (res) => {
      let raw = '';
      res.on('data', chunk => raw += chunk);
      res.on('end', () => resolve(JSON.parse(raw)));
    });
    req.on('error', reject);
    req.end();
  });

  const wsUrl = newTarget.webSocketDebuggerUrl;
  console.log('Target WS:', wsUrl);

  const ws = new WebSocket(wsUrl);

  let idCounter = 1;
  const callbacks = new Map();

  function send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = idCounter++;
      callbacks.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  await new Promise(r => ws.onopen = r);

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && callbacks.has(msg.id)) {
      const { resolve, reject } = callbacks.get(msg.id);
      callbacks.delete(msg.id);
      if (msg.error) reject(msg.error);
      else resolve(msg.result);
    } else if (msg.method === 'Runtime.consoleAPICalled') {
      const args = msg.params.args.map(a => a.value ?? a.description ?? JSON.stringify(a)).join(' ');
      console.log(`[BROWSER CONSOLE ${msg.params.type.toUpperCase()}]:`, args);
    } else if (msg.method === 'Runtime.exceptionThrown') {
      console.error('[BROWSER EXCEPTION]:', msg.params.exceptionDetails);
    }
  };

  await send('Runtime.enable');
  await send('Page.enable');
  await send('DOM.enable');

  console.log('Waiting 3s for page load...');
  await new Promise(r => setTimeout(r, 3000));

  // Check what projects are in the select dropdown
  const evalProjects = await send('Runtime.evaluate', {
    expression: `
      (() => {
        const sel = document.querySelector('select[aria-label="Select active project workspace"]');
        if (!sel) return { error: 'select not found', bodyHtml: document.body.innerHTML.slice(0, 500) };
        const options = Array.from(sel.options).map(o => ({ value: o.value, text: o.text }));
        return { selectedValue: sel.value, options };
      })()
    `,
    returnByValue: true
  });
  console.log('Initial select state:', evalProjects.result?.value);

  // Let's test switching projects to each option!
  const options = evalProjects.result?.value?.options || [];
  for (const opt of options) {
    console.log(`\n--- Switching to project: ${opt.text} (${opt.value}) ---`);
    const switchRes = await send('Runtime.evaluate', {
      expression: `
        (() => {
          const sel = document.querySelector('select[aria-label=\"Select active project workspace\"]');
          if (!sel) return { error: 'select not found' };
          sel.value = "${opt.value}";
          sel.dispatchEvent(new Event('change', { bubbles: true }));
          return { success: true, newVal: sel.value };
        })()
      `,
      returnByValue: true
    });
    console.log('Switch dispatch result:', switchRes.result?.value);
    await new Promise(r => setTimeout(r, 2000));

    // Check if body is blank or has content
    const bodyCheck = await send('Runtime.evaluate', {
      expression: `
        (() => {
          const root = document.getElementById('root');
          return {
            hasRoot: !!root,
            rootChildrenCount: root ? root.children.length : 0,
            rootTextSnippet: root ? root.innerText.slice(0, 200).replace(/\\n/g, ' ') : '',
            bodyClass: document.body.className
          };
        })()
      `,
      returnByValue: true
    });
    console.log('Post-switch UI state:', bodyCheck.result?.value);
  }

  // Also test clicking "Load Demo Area"
  console.log('\n--- Testing "Load Demo Area" click ---');
  const demoRes = await send('Runtime.evaluate', {
    expression: `
      (() => {
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Load Demo Area'));
        if (!btn) return { error: 'Load Demo Area button not found' };
        btn.click();
        return { clicked: true };
      })()
    `,
    returnByValue: true
  });
  console.log('Load demo click result:', demoRes.result?.value);
  await new Promise(r => setTimeout(r, 2000));

  const finalCheck = await send('Runtime.evaluate', {
    expression: `
      (() => {
        const root = document.getElementById('root');
        return {
          rootChildrenCount: root ? root.children.length : 0,
          rootTextSnippet: root ? root.innerText.slice(0, 200).replace(/\\n/g, ' ') : ''
        };
      })()
    `,
    returnByValue: true
  });
  console.log('Final UI state after Load Demo Area:', finalCheck.result?.value);

  ws.close();
  edge.kill();
}

run().catch(err => {
  console.error('Test run failed:', err);
  process.exit(1);
});
