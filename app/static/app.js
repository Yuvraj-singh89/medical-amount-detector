/**
 * Interactive Client JavaScript for Plum Assignment Problem 4 UI
 */

const PRESETS = {
  sample1: "Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%",
  sample2: "T0tal: Rs l200 | Pald: 1000 | Due: 200",
  sample3: "Apollo Specialty Hospital | Consultation: 500 | Medicines: 1500 | Total: INR 2000 | Paid: 1500 | Due: 500",
  noisy: "Doctor's Note: Patient presents with mild headache. Prescribed Rest and Hydration. No invoice generated."
};

let currentTab = 'text';
let selectedFile = null;
let lastStep4Data = null;

function switchTab(tab) {
  currentTab = tab;
  document.getElementById('tab-text-btn').classList.toggle('active', tab === 'text');
  document.getElementById('tab-image-btn').classList.toggle('active', tab === 'image');
  document.getElementById('text-tab-content').style.display = tab === 'text' ? 'block' : 'none';
  document.getElementById('image-tab-content').style.display = tab === 'image' ? 'block' : 'none';
  hideStatus();
}

function loadPreset(key) {
  if (PRESETS[key]) {
    document.getElementById('text-input').value = PRESETS[key];
  }
}

function clearInput() {
  document.getElementById('text-input').value = '';
  resetDisplay();
  hideStatus();
}

function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) {
    loadFile(file);
  }
}

function loadFile(file) {
  selectedFile = file;
  const reader = new FileReader();
  reader.onload = function(e) {
    const preview = document.getElementById('image-preview');
    preview.src = e.target.result;
    preview.style.display = 'block';
    document.querySelector('.drop-content').style.display = 'none';
    document.getElementById('process-image-btn').disabled = false;
  };
  reader.readAsDataURL(file);
}

function clearImage() {
  selectedFile = null;
  document.getElementById('file-input').value = '';
  document.getElementById('image-preview').style.display = 'none';
  document.querySelector('.drop-content').style.display = 'block';
  document.getElementById('process-image-btn').disabled = true;
  resetDisplay();
  hideStatus();
}

async function loadSampleImage(type) {
  try {
    const response = await fetch(`/samples/sample_${type}.png`);
    if (!response.ok) {
      alert("Sample image not yet generated or not found. Please upload an image directly.");
      return;
    }
    const blob = await response.blob();
    const file = new File([blob], `sample_${type}.png`, { type: 'image/png' });
    loadFile(file);
  } catch (err) {
    alert("Could not load sample image: " + err.message);
  }
}

function showStatus(message, isError) {
  const banner = document.getElementById('status-banner');
  banner.textContent = message;
  banner.className = `status-banner ${isError ? 'guardrail' : 'success'}`;
  banner.style.display = 'block';
}

function hideStatus() {
  document.getElementById('status-banner').style.display = 'none';
}

function resetDisplay() {
  document.getElementById('step1-conf').textContent = '-';
  document.getElementById('step1-curr').textContent = '-';
  document.getElementById('step1-tokens').innerHTML = '<span class="chip-placeholder">Awaiting execution...</span>';
  document.getElementById('step1-json').textContent = '{}';

  document.getElementById('step2-conf').textContent = '-';
  document.getElementById('step2-amounts').innerHTML = '<span class="chip-placeholder">Awaiting execution...</span>';
  document.getElementById('step2-json').textContent = '{}';

  document.getElementById('step3-conf').textContent = '-';
  document.getElementById('step3-list').innerHTML = '<div class="chip-placeholder">Awaiting execution...</div>';
  document.getElementById('step3-json').textContent = '{}';

  document.getElementById('step4-status').textContent = '-';
  document.getElementById('step4-curr').textContent = '-';
  document.getElementById('step4-json').textContent = '{}';
  document.getElementById('validation-box').style.display = 'none';
  lastStep4Data = null;
}

async function processText() {
  const text = document.getElementById('text-input').value.trim();
  if (!text) {
    alert("Please enter bill or receipt text first.");
    return;
  }

  hideStatus();
  resetDisplay();

  try {
    const res = await fetch('/api/v1/pipeline/steps-text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text })
    });

    const data = await res.json();
    handlePipelineResponse(data);
  } catch (err) {
    showStatus("API Error: " + err.message, true);
  }
}

async function processImage() {
  if (!selectedFile) {
    alert("Please select or drop an image file first.");
    return;
  }

  hideStatus();
  resetDisplay();

  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const res = await fetch('/api/v1/pipeline/steps-image', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    handlePipelineResponse(data);
  } catch (err) {
    showStatus("API Error: " + err.message, true);
  }
}

function handlePipelineResponse(data) {
  // Check if Guardrail was triggered
  if (data.status === "no_amounts_found" || data.guardrail_triggered) {
    const reason = data.reason || (data.guardrail_details && data.guardrail_details.reason) || "document too noisy";
    showStatus(`⚠️ Guardrail Triggered: status='no_amounts_found', reason='${reason}'`, true);
    document.getElementById('step4-json').textContent = JSON.stringify({
      status: "no_amounts_found",
      reason: reason
    }, null, 2);
    return;
  }

  showStatus("✓ Pipeline executed successfully across all 4 steps!", false);

  // Step 1
  if (data.step1) {
    document.getElementById('step1-conf').textContent = data.step1.confidence;
    document.getElementById('step1-curr').textContent = data.step1.currency_hint || 'INR';
    const tokensContainer = document.getElementById('step1-tokens');
    tokensContainer.innerHTML = '';
    data.step1.raw_tokens.forEach(tok => {
      const chip = document.createElement('span');
      chip.className = `token-chip ${tok.includes('%') ? 'percent' : ''}`;
      chip.textContent = tok;
      tokensContainer.appendChild(chip);
    });
    document.getElementById('step1-json').textContent = JSON.stringify(data.step1, null, 2);
  }

  // Step 2
  if (data.step2) {
    document.getElementById('step2-conf').textContent = data.step2.normalization_confidence;
    const amountsContainer = document.getElementById('step2-amounts');
    amountsContainer.innerHTML = '';
    data.step2.normalized_amounts.forEach(amt => {
      const chip = document.createElement('span');
      chip.className = 'token-chip';
      chip.textContent = amt;
      amountsContainer.appendChild(chip);
    });
    document.getElementById('step2-json').textContent = JSON.stringify(data.step2, null, 2);
  }

  // Step 3
  if (data.step3) {
    document.getElementById('step3-conf').textContent = data.step3.confidence;
    const listContainer = document.getElementById('step3-list');
    listContainer.innerHTML = '';
    data.step3.amounts.forEach(item => {
      const div = document.createElement('div');
      div.className = 'classified-item';
      div.innerHTML = `<span class="classified-type">${item.type}</span><span class="classified-val">${item.value}</span>`;
      listContainer.appendChild(div);
    });
    document.getElementById('step3-json').textContent = JSON.stringify(data.step3, null, 2);
  }

  // Step 4
  if (data.step4) {
    lastStep4Data = data.step4;
    document.getElementById('step4-status').textContent = data.step4.status;
    document.getElementById('step4-curr').textContent = data.step4.currency;
    document.getElementById('step4-json').textContent = JSON.stringify(data.step4, null, 2);
  }

  // Validation
  if (data.ai_validation_notes && data.ai_validation_notes.length > 0) {
    const valBox = document.getElementById('validation-box');
    const valNotes = document.getElementById('validation-notes');
    valNotes.innerHTML = data.ai_validation_notes.map(n => `<div>&bull; ${n}</div>`).join('');
    valBox.style.display = 'block';
  }
}

function copyFinalJson() {
  if (lastStep4Data) {
    navigator.clipboard.writeText(JSON.stringify(lastStep4Data, null, 2));
    alert("Final Step 4 JSON copied to clipboard!");
  } else {
    alert("No Step 4 result to copy.");
  }
}

// Drag & Drop
const dropZone = document.getElementById('drop-zone');
if (dropZone) {
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
  });
  function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }
  ['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.add('hover'), false);
  });
  ['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.remove('hover'), false);
  });
  dropZone.addEventListener('drop', handleDrop, false);
  function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) loadFile(files[0]);
  }
}

// Initialize default text
window.addEventListener('DOMContentLoaded', () => {
  loadPreset('sample1');
});
