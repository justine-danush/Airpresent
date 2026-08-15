const status = document.querySelector('#status');
const statusPill = document.querySelector('#statusPill');
const statusText = document.querySelector('#statusText');
const pairing = document.querySelector('#pairing');
const remote = document.querySelector('#remote');
const motionButton = document.querySelector('#motion');
const motionVis = document.querySelector('#motionVis');
const visPuck = document.querySelector('#visPuck');

let sessionToken;
let motionActive = false;
let baseline = null;
let lastSent = 0;
let receivedMotion = false;

function updateStatus(text, type = 'normal') {
  if (status) status.textContent = text;
  if (statusPill && statusText) {
    statusPill.className = 'status-pill ' + type;
    if (type === 'connected') statusText.textContent = 'Connected';
    else if (type === 'motion-active') statusText.textContent = 'Air Mouse Active';
    else statusText.textContent = 'Pairing Required';
  }
}

function send(event) {
  if (!sessionToken) return;
  fetch('/control', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({...event, token: sessionToken})
  }).catch(() => updateStatus('Connection lost. Refresh to reconnect.', 'error'));
}

function performPairing(code) {
  if (!code || code.length !== 6) return updateStatus('Enter the 6-digit PIN code displayed on your PC screen.');
  updateStatus('Authenticating PIN code…');
  fetch('/pair', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({code})
  })
    .then(response => {
      if (response.status === 429) throw new Error('Security Rate Limit: Wait 60s');
      return response.json();
    })
    .then(reply => {
      if (reply.ok && reply.token) {
        sessionToken = reply.token;
        pairing.hidden = true;
        remote.hidden = false;
        updateStatus('Connected to PC. Ready for presentation.', 'connected');
      } else {
        updateStatus(reply.error || 'Invalid PIN code. Check your PC screen.', 'error');
      }
    })
    .catch(err => updateStatus(err.message || 'Could not reach PC. Check Wi-Fi connection.', 'error'));
}

document.querySelector('#connect').onclick = () => {
  const code = document.querySelector('#code').value.replace(/[^a-z0-9]/gi, '').toUpperCase();
  performPairing(code);
};

const showSettingsBtn = document.querySelector('#showSettings');
if (showSettingsBtn) {
  showSettingsBtn.onclick = () => {
    pairing.hidden = false;
    remote.hidden = true;
    updateStatus('Enter PC address or 6-digit PIN.');
  };
}

// Check for QR code auto-pairing in URL hash or query params (#code=123456 or ?code=123456)
window.addEventListener('DOMContentLoaded', () => {
  let autoCode = '';
  const hashMatch = window.location.hash.match(/code=([a-zA-Z0-9]{6})/);
  const searchMatch = window.location.search.match(/code=([a-zA-Z0-9]{6})/);
  if (hashMatch) autoCode = hashMatch[1];
  else if (searchMatch) autoCode = searchMatch[1];

  if (autoCode) {
    const codeInput = document.querySelector('#code');
    if (codeInput) codeInput.value = autoCode;
    performPairing(autoCode);
  }
});

document.querySelectorAll('[data-click]').forEach(button =>
  button.onclick = () => send({type: 'click', button: button.dataset.click})
);
document.querySelectorAll('[data-key]').forEach(button =>
  button.onclick = () => send({type: 'key', key: button.dataset.key})
);
document.querySelector('#escape').onclick = () => send({type: 'key', key: 'escape'});

async function enableMotion() {
  if (!motionActive && typeof DeviceOrientationEvent.requestPermission === 'function') {
    try {
      await DeviceOrientationEvent.requestPermission();
    } catch {
      updateStatus('Trying motion sensor…', 'connected');
    }
  }
  motionActive = !motionActive;
  baseline = null;
  receivedMotion = false;
  
  const heroText = motionButton.querySelector('.hero-text') || motionButton;
  heroText.textContent = motionActive ? 'Pause Air Cursor' : 'Start Air Cursor';
  motionButton.classList.toggle('active', motionActive);
  if (motionVis) motionVis.hidden = !motionActive;

  if (motionActive) {
    updateStatus('Air Mouse active — tilt phone to move cursor', 'motion-active');
    setTimeout(() => {
      if (motionActive && !receivedMotion) updateStatus('Browser blocks motion over HTTP. Use buttons or native app.', 'connected');
    }, 1800);
  } else {
    updateStatus('Connected to PC. Motion paused.', 'connected');
  }
}
motionButton.onclick = enableMotion;

let smoothDx = 0, smoothDy = 0;

window.addEventListener('deviceorientation', event => {
  if (!motionActive || event.beta == null || event.gamma == null) return;
  receivedMotion = true;
  if (!baseline) { baseline = {beta: event.beta, gamma: event.gamma}; return; }
  const now = performance.now();
  if (now - lastSent < 20) return;
  lastSent = now;
  
  const rawDx = (event.gamma - baseline.gamma);
  const rawDy = (event.beta - baseline.beta);
  
  if (visPuck) {
    const px = Math.max(-45, Math.min(45, rawDx * 4));
    const py = Math.max(-45, Math.min(45, rawDy * 4));
    visPuck.style.transform = `translate(${px}px, ${py}px)`;
  }

  let dx = rawDx * 2.1;
  let dy = rawDy * 2.1;
  const speed = Math.hypot(dx, dy);

  // Tremor Suppression & Low-pass filter
  if (speed < 0.4) {
    smoothDx *= 0.4;
    smoothDy *= 0.4;
  } else {
    const alpha = Math.min(1.0, Math.max(0.3, speed / 4.0));
    smoothDx = alpha * dx + (1 - alpha) * smoothDx;
    smoothDy = alpha * dy + (1 - alpha) * smoothDy;
    send({type: 'move', dx: smoothDx, dy: smoothDy});
  }
  baseline = {beta: event.beta, gamma: event.gamma};
});

if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js?v=6');
