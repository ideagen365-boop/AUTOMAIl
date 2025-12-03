
const uploadBtn = document.getElementById('uploadBtn');
const excelFile = document.getElementById('excelFile');
const uploadStatus = document.getElementById('uploadStatus');

const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const controlStatus = document.getElementById('controlStatus');

const messageEl = document.getElementById('message');
const subjectEl = document.getElementById('subject');
const resumeEl = document.getElementById('resumeFile');

const totalEl = document.getElementById('total');
const sentEl = document.getElementById('sent');
const runningEl = document.getElementById('running');
const lastErrorEl = document.getElementById('lastError');
const logList = document.getElementById('logList');

let statusInterval = null;

function setStatus(element, text, ok = true) {
  element.textContent = text;
  element.className = ok ? 'status ok' : 'status error';
}

uploadBtn.addEventListener('click', async () => {
  const file = excelFile.files[0];
  if (!file) {
    setStatus(uploadStatus, 'Please select an Excel file.', false);
    return;
  }
  const formData = new FormData();
  formData.append('file', file);

  setStatus(uploadStatus, 'Uploading...');
  try {
    const res = await fetch('/upload-excel', { method: 'POST', body: formData });
    const data = await res.json();
    if (!data.ok) {
      setStatus(uploadStatus, data.error || 'Upload failed.', false);
      return;
    }
    setStatus(uploadStatus, `Uploaded. ${data.total} recipients loaded.`);
    totalEl.textContent = data.total;
    sentEl.textContent = '0';
  } catch {
    setStatus(uploadStatus, 'Network error during upload.', false);
  }
});

startBtn.addEventListener('click', async () => {
  const message = messageEl.value.trim();
  const subject = subjectEl.value.trim() || 'Notification';
  const resumeFile = resumeEl.files[0] || null;

  if (!message) {
    setStatus(controlStatus, 'Message cannot be empty.', false);
    return;
  }

  const formData = new FormData();
  formData.append('message', message);
  formData.append('subject', subject);
  if (resumeFile) formData.append('resume', resumeFile);

  setStatus(controlStatus, 'Starting...');
  try {
    const res = await fetch('/start', { method: 'POST', body: formData });
    const data = await res.json();
    if (!data.ok) {
      setStatus(controlStatus, data.error || 'Start failed.', false);
      return;
    }
    setStatus(controlStatus, 'Started sending.');
    startStatusPolling();
  } catch {
    setStatus(controlStatus, 'Network error on start.', false);
  }
});

stopBtn.addEventListener('click', async () => {
  setStatus(controlStatus, 'Stopping...');
  try {
    const res = await fetch('/stop', { method: 'POST' });
    const data = await res.json();
    setStatus(controlStatus, data.message || 'Stopped.');
  } catch {
    setStatus(controlStatus, 'Network error on stop.', false);
  }
});

function startStatusPolling() {
  if (statusInterval) return;
  statusInterval = setInterval(async () => {
    try {
      const res = await fetch('/status');
      const data = await res.json();
      if (!data.ok) return;

      totalEl.textContent = data.total;
      sentEl.textContent = data.sent;
      runningEl.textContent = data.running ? 'true' : 'false';
      lastErrorEl.textContent = data.last_error || 'None';

      logList.innerHTML = '';
      (data.log || []).forEach(item => {
        const li = document.createElement('li');
        li.textContent = `${item.email}: ${item.status}${item.error ? ' (' + item.error + ')' : ''}`;
        li.className = item.status === 'sent' ? 'log-sent' : 'log-failed';
        logList.appendChild(li);
      });

      if (!data.running) {
        clearInterval(statusInterval);
        statusInterval = null;
      }
    } catch {}
  }, 2000);
}
