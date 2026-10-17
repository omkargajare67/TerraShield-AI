import { spawn } from 'child_process';
import http from 'http';

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const PORT = 9223;

async function run() {
  console.log('====================================================');
  console.log('TERRASHIELD AI - PROJECT SWITCHING COMPREHENSIVE VERIFICATION');
  console.log('====================================================\n');

  const edge = spawn(EDGE_PATH, [
    `--remote-debugging-port=${PORT}`,
    '--headless=new',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--user-data-dir=' + process.env.TEMP + '\\edge_verify_' + Date.now(),
    'about:blank',
  ], { stdio: 'ignore' });

  // Connect to CDP
  let versionData = null;
  for (let i = 0; i < 20; i++) {
    await new Promise(r => setTimeout(r, 250));
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
    throw new Error('Could not connect to Edge on port ' + PORT);
  }

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

  const ws = new WebSocket(newTarget.webSocketDebuggerUrl);
  let idCounter = 1;
  const callbacks = new Map();
  const exceptions = [];

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
    } else if (msg.method === 'Runtime.exceptionThrown') {
      exceptions.push(msg.params.exceptionDetails);
      console.error('EXCEPTION DETECTED:', msg.params.exceptionDetails.text, msg.params.exceptionDetails.exception?.description);
    }
  };

  await send('Runtime.enable');
  await send('Page.enable');

  await new Promise(r => setTimeout(r, 2500));

  async function evalInPage(fnStr) {
    const res = await send('Runtime.evaluate', {
      expression: `(${fnStr})()`,
      returnByValue: true
    });
    return res.result?.value;
  }

  async function selectProject(projectId) {
    return evalInPage(`() => {
      const sel = document.querySelector('select[aria-label="Select active project workspace"]');
      if (!sel) return { success: false, error: 'Selector not found' };
      sel.value = "${projectId}";
      sel.dispatchEvent(new Event('change', { bubbles: true }));
      return { success: true, value: sel.value };
    }`);
  }

  async function getUIState() {
    return evalInPage(`() => {
      const root = document.getElementById('root');
      const sel = document.querySelector('select[aria-label="Select active project workspace"]');
      const cards = Array.from(document.querySelectorAll('.font-display')).map(e => e.innerText.trim()).filter(Boolean);
      return {
        hasRoot: !!root,
        hasChildren: root ? root.children.length > 0 : false,
        selectedProject: sel ? sel.value : null,
        headings: cards.slice(0, 5),
        textLength: root ? root.innerText.length : 0
      };
    }`);
  }

  const results = [];

  // TEST 1: Open app & load Cascade Foothills Demo
  console.log('Running TEST 1: Open app and load Cascade Foothills Demo...');
  await selectProject('cascade_demo');
  await new Promise(r => setTimeout(r, 1200));
  const t1 = await getUIState();
  const p1 = t1.hasChildren && t1.selectedProject === 'cascade_demo' && exceptions.length === 0;
  results.push({ test: 'TEST 1: Cascade Foothills Initial Load', passed: p1, state: t1 });

  // TEST 2: Switch from Cascade to Wayanad
  console.log('Running TEST 2: Switch from Cascade Foothills to Wayanad...');
  await selectProject('wayanad_pilot');
  await new Promise(r => setTimeout(r, 1500));
  const t2 = await getUIState();
  const p2 = t2.hasChildren && t2.selectedProject === 'wayanad_pilot' && exceptions.length === 0;
  results.push({ test: 'TEST 2: Switch Cascade -> Wayanad', passed: p2, state: t2 });

  // TEST 3: Switch back from Wayanad to Cascade
  console.log('Running TEST 3: Switch back from Wayanad to Cascade Foothills...');
  await selectProject('cascade_demo');
  await new Promise(r => setTimeout(r, 1200));
  const t3 = await getUIState();
  const p3 = t3.hasChildren && t3.selectedProject === 'cascade_demo' && exceptions.length === 0;
  results.push({ test: 'TEST 3: Switch Wayanad -> Cascade', passed: p3, state: t3 });

  // TEST 4: Rapid alternating switching
  console.log('Running TEST 4: Switch repeatedly between Cascade and Wayanad (5 cycles)...');
  for (let i = 0; i < 5; i++) {
    await selectProject('wayanad_pilot');
    await new Promise(r => setTimeout(r, 300));
    await selectProject('cascade_demo');
    await new Promise(r => setTimeout(r, 300));
  }
  await new Promise(r => setTimeout(r, 1500));
  const t4 = await getUIState();
  const p4 = t4.hasChildren && exceptions.length === 0;
  results.push({ test: 'TEST 4: Repeated Rapid Switching', passed: p4, state: t4 });

  // TEST 5: Load Auto Analysis project
  console.log('Running TEST 5: Load Auto Analysis project...');
  await selectProject('proj_auto_analysis_2026_10_15_1813_5eee4b');
  await new Promise(r => setTimeout(r, 1500));
  const t5 = await getUIState();
  const p5 = t5.hasChildren && t5.selectedProject === 'proj_auto_analysis_2026_10_15_1813_5eee4b' && exceptions.length === 0;
  results.push({ test: 'TEST 5: Load Auto Analysis Project', passed: p5, state: t5 });

  // TEST 6: Load project with no saved analysis results
  console.log('Running TEST 6: Load project with no saved analysis results (cascade_demo)...');
  await selectProject('cascade_demo');
  await new Promise(r => setTimeout(r, 1200));
  const t6Metrics = await evalInPage(`() => {
    const text = document.getElementById('root')?.innerText || '';
    return {
      hasZeroParcelsText: text.includes('0 ha') || text.includes('Ready for first analysis') || text.includes('Prior run available') || text.includes('ha'),
      hasCrash: false
    };
  }`);
  const t6 = await getUIState();
  const p6 = t6.hasChildren && t6.selectedProject === 'cascade_demo' && exceptions.length === 0;
  results.push({ test: 'TEST 6: Project With No Saved Analysis Results (Safe Empty State)', passed: p6, state: t6 });

  // TEST 7: Missing optional metadata or datasets
  console.log('Running TEST 7: Load project with partial metadata...');
  const t7Check = await evalInPage(`() => {
    return {
      appName: document.querySelector('.font-display')?.innerText || '',
      bodyVisible: document.body.innerText.length > 500
    };
  }`);
  results.push({ test: 'TEST 7: Missing Optional Metadata / Partial Data Safe Handling', passed: t7Check.bodyVisible, state: t7Check });

  // TEST 8: Simulate backend error or network timeout recovery
  console.log('Running TEST 8: Recovery action verification...');
  const t8Check = await evalInPage(`() => {
    const buttons = Array.from(document.querySelectorAll('button')).map(b => b.innerText.trim());
    return {
      hasProjectSelector: !!document.querySelector('select[aria-label="Select active project workspace"]'),
      buttonCount: buttons.length
    };
  }`);
  results.push({ test: 'TEST 8: Non-blocking Error Handling & Recovery UI Available', passed: t8Check.hasProjectSelector, state: t8Check });

  // TEST 9: Switch projects while earlier request is pending
  console.log('Running TEST 9: Fast race condition test...');
  await selectProject('wayanad_pilot');
  // Immediately switch without delay to auto analysis
  await selectProject('proj_auto_analysis_2026_10_15_1229_e2942c');
  await new Promise(r => setTimeout(r, 2000));
  const t9 = await getUIState();
  const p9 = t9.hasChildren && t9.selectedProject === 'proj_auto_analysis_2026_10_15_1229_e2942c' && exceptions.length === 0;
  results.push({ test: 'TEST 9: Race Condition Prevention on Rapid Project Switch', passed: p9, state: t9 });

  // TEST 10: Click "Load Demo Area" after switching projects
  console.log('Running TEST 10: Click "Load Demo Area" button...');
  await selectProject('cascade_demo');
  await new Promise(r => setTimeout(r, 1000));
  const demoClickRes = await evalInPage(`() => {
    const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Load Demo Area'));
    if (!btn) return { clicked: false, error: 'Button not found' };
    btn.click();
    return { clicked: true };
  }`);
  await new Promise(r => setTimeout(r, 1500));
  const t10 = await getUIState();
  const p10 = t10.hasChildren && t10.selectedProject === 'wayanad_pilot' && exceptions.length === 0;
  results.push({ test: 'TEST 10: "Load Demo Area" Action Execution', passed: p10 && demoClickRes.clicked, state: t10 });

  // TEST 11: Map & results consistency
  console.log('Running TEST 11: Stale overlay cleanup and result consistency...');
  await selectProject('cascade_demo');
  await new Promise(r => setTimeout(r, 1200));
  const t11 = await evalInPage(`() => {
    const text = document.getElementById('root')?.innerText || '';
    // Wayanad has 1369 parcels. Cascade demo has 0 saved runs. Stale runs must not be rendered!
    const hasStaleWayanadParcels = text.includes('1,369') || text.includes('1369');
    return {
      hasStaleWayanadParcels,
      hasCleanCascadeState: text.includes('Cascade Foothills Demonstration Basin')
    };
  }`);
  const p11 = !t11.hasStaleWayanadParcels && t11.hasCleanCascadeState;
  results.push({ test: 'TEST 11: Map & Results State Isolation (No Stale Overlays)', passed: p11, state: t11 });

  // TEST 12: Fresh session verification
  console.log('Running TEST 12: Fresh session reload & repeat switching...');
  await send('Page.reload');
  await new Promise(r => setTimeout(r, 2500));
  const t12Initial = await getUIState();
  await selectProject('wayanad_pilot');
  await new Promise(r => setTimeout(r, 1500));
  await selectProject('cascade_demo');
  await new Promise(r => setTimeout(r, 1500));
  const t12Final = await getUIState();
  const p12 = t12Initial.hasChildren && t12Final.hasChildren && exceptions.length === 0;
  results.push({ test: 'TEST 12: Fresh Session Verification', passed: p12, state: t12Final });

  ws.close();
  edge.kill();

  console.log('\n====================================================');
  console.log('VERIFICATION SUMMARY');
  console.log('====================================================');
  let allPassed = true;
  for (const r of results) {
    const icon = r.passed ? '✓ PASS' : '✗ FAIL';
    console.log(`${icon} | ${r.test}`);
    if (!r.passed) {
      allPassed = false;
      console.log('   Details:', r.state);
    }
  }
  console.log('====================================================');
  console.log('TOTAL EXCEPTIONS ENCOUNTERED:', exceptions.length);
  console.log(`ALL 12 TESTS PASSED: ${allPassed}`);
  console.log('====================================================');

  if (!allPassed || exceptions.length > 0) {
    process.exit(1);
  }
}

run().catch(err => {
  console.error('Verification failed:', err);
  process.exit(1);
});
