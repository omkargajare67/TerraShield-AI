import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const PORT = 9227;

async function capture() {
  const edge = spawn(EDGE_PATH, [
    `--remote-debugging-port=${PORT}`,
    '--headless=new',
    '--window-size=1600,1050',
    '--disable-gpu',
    '--user-data-dir=' + process.env.TEMP + '\\edge_ss2_' + Date.now(),
    'about:blank'
  ], { stdio: 'ignore' });

  for (let i = 0; i < 20; i++) {
    await new Promise(r => setTimeout(r, 250));
    try {
      const v = await new Promise((res, rej) => {
        http.get(`http://127.0.0.1:${PORT}/json/version`, r => {
          let d = ''; r.on('data', c => d += c); r.on('end', () => res(JSON.parse(d)));
        }).on('error', rej);
      });
      if (v) break;
    } catch {}
  }

  const target = await new Promise((res, rej) => {
    const req = http.request({
      hostname: '127.0.0.1', port: PORT, path: '/json/new?http://127.0.0.1:5173', method: 'PUT'
    }, r => {
      let d = ''; r.on('data', c => d += c); r.on('end', () => res(JSON.parse(d)));
    });
    req.on('error', rej);
    req.end();
  });

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let id = 1;
  const send = (method, params = {}) => new Promise((resolve) => {
    const msgId = id++;
    const handler = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.id === msgId) {
        ws.removeEventListener('message', handler);
        resolve(msg.result);
      }
    };
    ws.addEventListener('message', handler);
    ws.send(JSON.stringify({ id: msgId, method, params }));
  });

  await new Promise(r => ws.onopen = r);
  await send('Page.enable');
  await new Promise(r => setTimeout(r, 3000));

  // Select Wayanad demo project
  await send('Runtime.evaluate', {
    expression: `(() => {
      const select = document.querySelector('select[aria-label="Select active project workspace"]');
      if (select) {
        select.value = 'wayanad_pilot';
        select.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
      }
      return false;
    })()`,
    returnByValue: true
  });
  console.log('Switched to wayanad_pilot...');

  await new Promise(r => setTimeout(r, 3000));

  // Navigate to 'Map Explorer' tab
  await send('Runtime.evaluate', {
    expression: `(() => {
      const tabs = Array.from(document.querySelectorAll('button[role="tab"]'));
      const mapTab = tabs.find(t => t.innerText.includes('Map Explorer'));
      if (mapTab) {
        mapTab.click();
        return true;
      }
      return false;
    })()`,
    returnByValue: true
  });
  console.log('Navigated to Map Explorer tab...');

  await new Promise(r => setTimeout(r, 4500));

  // Click on a tree marker or select parcel PARCEL-R33-C13
  const clickParcel = await send('Runtime.evaluate', {
    expression: `(() => {
      const markers = Array.from(document.querySelectorAll('.terra-tree-marker'));
      if (markers.length > 0) {
        markers[0].click();
        return { clickedMarker: true, count: markers.length };
      }
      return { clickedMarker: false, count: 0 };
    })()`,
    returnByValue: true
  });
  console.log('Tree Marker Click Result:', clickParcel?.result?.value);

  await new Promise(r => setTimeout(r, 2000));

  const ss = await send('Page.captureScreenshot', { format: 'png' });
  if (ss && ss.data) {
    fs.mkdirSync('C:\\TERRASHIELD AI\\dist', { recursive: true });
    fs.writeFileSync('C:\\TERRASHIELD AI\\dist\\wayanad_parcels_inspection.png', Buffer.from(ss.data, 'base64'));
    console.log('SUCCESS: Captured dist/wayanad_parcels_inspection.png');
  }

  ws.close();
  edge.kill();
}

capture().catch(console.error);
