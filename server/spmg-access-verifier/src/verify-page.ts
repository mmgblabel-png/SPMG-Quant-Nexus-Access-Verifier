import type { ServerResponse } from 'node:http';

export function sendVerificationPage(response: ServerResponse): void {
  const html = String.raw\`<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>SPMG Quant Nexus — Access Verification</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, system-ui, sans-serif; }
    body { margin:0; min-height:100vh; display:grid; place-items:center; background:#05080d; color:#eef7ff; }
    .card { width:min(680px, calc(100% - 32px)); border:1px solid #1b3241; background:#0a1119; border-radius:20px; padding:28px; box-shadow:0 20px 70px rgba(0,0,0,.45); }
    h1 { margin:0 0 8px; font-size:30px; }
    .sub { color:#8aa6b7; margin:0 0 24px; }
    .accent { color:#36d9ff; }
    button { width:100%; border:0; border-radius:12px; padding:14px 16px; font-size:16px; font-weight:700; cursor:pointer; background:linear-gradient(90deg,#16bce8,#d7a83b); color:#041018; }
    button:disabled { opacity:.5; cursor:not-allowed; }
    .status { margin-top:20px; padding:16px; border-radius:12px; background:#071018; border:1px solid #142936; white-space:pre-wrap; word-break:break-word; min-height:72px; }
    .token { margin-top:12px; padding:12px; border-radius:10px; background:#03070b; border:1px solid #163241; font-family:ui-monospace,monospace; word-break:break-all; display:none; }
    .copy { margin-top:10px; background:#152531; color:#dff8ff; display:none; }
    .safe { margin-top:20px; color:#8aa6b7; font-size:13px; line-height:1.5; }
  </style>
</head>
<body>
  <main class="card">
    <h1>SPMG <span class="accent">Quant Nexus</span></h1>
    <p class="sub">Verify your wallet to unlock your Access Key tier.</p>

    <button id="connect">Connect Wallet & Verify</button>
    <div id="status" class="status">Ready. No transaction will be created.</div>
    <div id="token" class="token"></div>
    <button id="copy" class="copy">Copy Session Token</button>

    <p class="safe">
      Security: this page only asks you to sign a readable verification message.
      Never enter a seed phrase or private key. No blockchain transaction is requested.
    </p>
  </main>

<script>
const connect = document.getElementById('connect');
const status = document.getElementById('status');
const tokenBox = document.getElementById('token');
const copy = document.getElementById('copy');
let sessionToken = '';

async function json(url, options) {
  const res = await fetch(url, options);
  let body = {};
  try { body = await res.json(); } catch {}
  if (!res.ok) throw new Error(body.error || ('HTTP ' + res.status));
  return body;
}

connect.addEventListener('click', async () => {
  connect.disabled = true;
  tokenBox.style.display = 'none';
  copy.style.display = 'none';
  sessionToken = '';

  try {
    if (!window.ethereum) throw new Error('No EVM wallet detected. Open this page in a browser with MetaMask or another compatible wallet.');

    status.textContent = 'Connecting wallet...';
    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
    const wallet = accounts && accounts[0];
    if (!wallet) throw new Error('No wallet account returned.');

    status.textContent = 'Creating secure challenge...';
    const challenge = await json('/api/spmg/wallet/challenge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ wallet })
    });

    status.textContent = 'Please sign the SPMG verification message in your wallet.';
    const signature = await window.ethereum.request({
      method: 'personal_sign',
      params: [challenge.message, wallet]
    });

    status.textContent = 'Verifying signature...';
    const verified = await json('/api/spmg/wallet/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        wallet,
        nonce: challenge.nonce,
        signature
      })
    });

    sessionToken = verified.sessionToken;
    status.textContent = 'Checking SPMG Access Key ownership...';

    const access = await json('/api/spmg/access?sessionToken=' + encodeURIComponent(sessionToken), {
      method: 'GET'
    });

    status.textContent =
      'VERIFIED\\n' +
      'Wallet: ' + access.wallet + '\\n' +
      'Access tier: ' + access.tier + '\\n' +
      'Session expires: ' + verified.expiresAt;

    tokenBox.textContent = sessionToken;
    tokenBox.style.display = 'block';
    copy.style.display = 'block';
  } catch (error) {
    status.textContent = 'Verification failed: ' + (error && error.message ? error.message : String(error));
  } finally {
    connect.disabled = false;
  }
});

copy.addEventListener('click', async () => {
  if (!sessionToken) return;
  await navigator.clipboard.writeText(sessionToken);
  copy.textContent = 'Session Token Copied';
  setTimeout(() => { copy.textContent = 'Copy Session Token'; }, 1800);
});
</script>
</body>
</html>\`;

  response.writeHead(200, {
    'Content-Type': 'text/html; charset=utf-8',
    'Cache-Control': 'no-store',
    'Content-Security-Policy': "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
  });
  response.end(html);
}
