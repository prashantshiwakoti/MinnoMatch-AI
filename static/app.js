/**
 * MinnoMatch AI - Frontend Application Controller
 * Metropolia UAS 10-ECTS Multidisciplinary Innovation Projects
 */

let currentSynthesizedData = null;

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initSynthesizer();
  initMatcher();
  initCatalogFilters();
  initSettings();
  fetchStatus();
});

// 1. TAB NAVIGATION
function initTabs() {
  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));

      tab.classList.add('active');
      const targetId = tab.dataset.tab;
      const targetContent = document.getElementById(targetId);
      if (targetContent) {
        targetContent.classList.remove('hidden');
      }
    });
  });
}

// 2. QUICK PRESET PILLS
window.setPrompt = function(text) {
  const textarea = document.getElementById('challengePrompt');
  if (textarea) {
    textarea.value = text;
    textarea.focus();
  }
};

// 3. CHALLENGE SYNTHESIZER
function initSynthesizer() {
  const form = document.getElementById('synthesizeForm');
  const btn = document.getElementById('synthesizeBtn');
  const btnText = btn.querySelector('.btn-text');
  const spinner = btn.querySelector('.btn-spinner');
  const placeholder = document.getElementById('synthesizePlaceholder');
  const resultContainer = document.getElementById('synthesizeResult');
  const actionButtons = document.getElementById('outputActionButtons');
  const saveBtn = document.getElementById('saveChallengeBtn');
  const viewCharterBtn = document.getElementById('viewCharterBtn');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const prompt = document.getElementById('challengePrompt').value.trim();
    if (!prompt) return;

    // Set loading state
    btn.disabled = true;
    btnText.textContent = 'Synthesizing with AI...';
    spinner.classList.remove('hidden');

    try {
      const res = await fetch('/api/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      });

      const data = await res.json();
      if (data.success && data.result) {
        currentSynthesizedData = data.result;
        renderSynthesis(data.result);
        placeholder.classList.add('hidden');
        resultContainer.classList.remove('hidden');
        actionButtons.classList.remove('hidden');
      } else {
        alert(data.error || 'Failed to synthesize project');
      }
    } catch (err) {
      console.error(err);
      alert('Error connecting to backend server');
    } finally {
      btn.disabled = false;
      btnText.textContent = '🚀 Synthesize Multidisciplinary Plan';
      spinner.classList.add('hidden');
    }
  });

  saveBtn.addEventListener('click', async () => {
    if (!currentSynthesizedData) return;
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';

    try {
      const res = await fetch('/api/challenges', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentSynthesizedData)
      });
      const data = await res.json();
      if (data.success) {
        saveBtn.textContent = '✅ Saved to Catalog!';
        setTimeout(() => {
          saveBtn.disabled = false;
          saveBtn.textContent = '💾 Save to Catalog';
        }, 2500);
        reloadChallengesCatalog();
      }
    } catch (err) {
      console.error(err);
      saveBtn.textContent = 'Error Saving';
    }
  });

  viewCharterBtn.addEventListener('click', () => {
    if (currentSynthesizedData) {
      viewProjectCharter(currentSynthesizedData);
    }
  });
}

function renderSynthesis(data) {
  const container = document.getElementById('synthesizeResult');

  const sdgBadges = (data.sdgs || []).map(sdg => 
    `<span class="sdg-tag">${sdg}</span>`
  ).join('');

  const wpCards = (data.work_packages || []).map(wp => `
    <div class="wp-card">
      <div class="wp-header">
        <span class="wp-faculty-title">${wp.faculty}</span>
        <span class="campus-badge badge-tech" style="font-size:0.7rem;">${wp.campus.split(' ')[0]}</span>
      </div>
      <div class="wp-role">${wp.role}</div>
      <div class="wp-desc">${wp.contribution}</div>
    </div>
  `).join('');

  const milestonesList = (data.milestones || []).map(m => 
    `<li>${m}</li>`
  ).join('');

  container.innerHTML = `
    <h3 class="synth-title">${data.title}</h3>
    <div class="synth-statement">${data.challenge_statement}</div>
    <div class="sdg-tag-row">${sdgBadges}</div>
    
    <h4 style="font-size:0.9rem; margin-bottom:0.6rem; font-weight:700;">Multidisciplinary Work Packages:</h4>
    <div class="work-packages-container">${wpCards}</div>

    <div class="academic-box">
      <strong>🔬 Academic R&D Potential:</strong><br>
      ${data.academic_potential}
    </div>

    <div class="milestones-box">
      <h4>12-Week Sprint Milestones (10 ECTS):</h4>
      <ul class="milestones-list">${milestonesList}</ul>
    </div>
  `;
}

// 4. STUDENT MATCHER
function initMatcher() {
  const form = document.getElementById('matcherForm');
  const container = document.getElementById('matchResultsContainer');
  const btn = document.getElementById('matchBtn');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const faculty = document.getElementById('studentFaculty').value;
    const degree = document.getElementById('studentDegree').value;
    const skills = document.getElementById('studentSkills').value;
    const interests = document.getElementById('studentInterests').value;

    btn.disabled = true;
    btn.textContent = 'Calculating Cross-Disciplinary Synergy...';

    try {
      const res = await fetch('/api/match-student', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ faculty, degree, skills, interests })
      });
      const data = await res.json();

      if (data.success && data.matches) {
        renderMatches(data.matches, container);
      }
    } catch (err) {
      console.error(err);
      alert('Error calculating student matches');
    } finally {
      btn.disabled = false;
      btn.textContent = '🔍 Match Me to Active Innovation Projects';
    }
  });
}

function renderMatches(matches, container) {
  if (!matches || matches.length === 0) {
    container.innerHTML = '<p class="placeholder-state">No matching projects found.</p>';
    return;
  }

  container.innerHTML = matches.map(m => `
    <div class="match-card">
      <div class="match-header">
        <strong style="font-size:0.95rem;">${m.challenge_title}</strong>
        <span class="match-score-badge">${m.compatibility_score}% Compatibility</span>
      </div>
      <div class="match-progress-bar">
        <div class="match-progress-fill" style="width: ${m.compatibility_score}%;"></div>
      </div>
      <div class="match-role-title">Recommended Role: ${m.recommended_role}</div>
      <div class="match-role-desc"><strong>Your Cross-Faculty Contribution:</strong> ${m.tailored_contribution}</div>
      <div style="font-size:0.78rem; color:var(--text-muted);">
        📍 Campus Anchor: ${m.campus} &bull; Faculty: ${m.faculty}
      </div>
    </div>
  `).join('');
}

// 5. CATALOG FILTERS & RELOAD
function initCatalogFilters() {
  const buttons = document.querySelectorAll('.filter-btn');
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const filter = btn.dataset.filter;

      const cards = document.querySelectorAll('#challengesCatalog .challenge-card');
      cards.forEach(card => {
        if (filter === 'all' || card.dataset.campuses.toLowerCase().includes(filter.toLowerCase())) {
          card.classList.remove('hidden');
        } else {
          card.classList.add('hidden');
        }
      });
    });
  });
}

async function reloadChallengesCatalog() {
  try {
    const res = await fetch('/api/challenges');
    const data = await res.json();
    if (data.success && data.challenges) {
      document.getElementById('challengeCountBadge').textContent = data.challenges.length;
      const catalog = document.getElementById('challengesCatalog');
      catalog.innerHTML = data.challenges.map(c => `
        <div class="challenge-card" data-campuses="${(c.campus_synergy || []).join(' ')}">
          <div class="challenge-top">
            <span class="challenge-id">${c.id}</span>
            <div class="sdg-tags">
              ${(c.sdgs || []).map(sdg => `<span class="sdg-badge">${sdg.split(':')[0]}</span>`).join('')}
            </div>
          </div>
          <h3 class="challenge-title">${c.title}</h3>
          <p class="challenge-desc">${c.challenge_statement}</p>

          <div class="work-packages-preview">
            <h4>Multidisciplinary Campus Allocation:</h4>
            <div class="wp-tags">
              ${(c.work_packages || []).map(wp => `
                <div class="wp-tag">
                  <strong>${wp.campus.split(' ')[0]}:</strong> ${wp.role}
                </div>
              `).join('')}
            </div>
          </div>

          <div class="academic-note">
            <strong>🔬 Academic Scope:</strong> ${c.academic_potential}
          </div>

          <div class="challenge-card-footer">
            <button class="btn btn-outline btn-sm" onclick='viewProjectCharter(${JSON.stringify(c)})'>📄 View 10-ECTS Charter</button>
          </div>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to reload catalog', err);
  }
}

// 6. CHARTER MODAL
window.viewProjectCharter = async function(challengeObj) {
  try {
    const res = await fetch('/api/export-charter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(challengeObj)
    });
    const data = await res.json();
    if (data.success && data.markdown) {
      document.getElementById('charterMarkdownPreview').textContent = data.markdown;
      openModal('charterModal');
    }
  } catch (err) {
    console.error(err);
    alert('Error generating charter');
  }
};

window.openModal = function(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('hidden');
};

window.closeModal = function(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('hidden');
};

document.getElementById('copyCharterBtn').addEventListener('click', () => {
  const text = document.getElementById('charterMarkdownPreview').textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById('copyCharterBtn');
    btn.textContent = '✅ Copied!';
    setTimeout(() => { btn.textContent = '📋 Copy Markdown'; }, 2000);
  });
});

// 7. SETTINGS & STATUS
function initSettings() {
  const openBtn = document.getElementById('openSettingsBtn');
  const form = document.getElementById('settingsForm');

  openBtn.addEventListener('click', () => {
    openModal('settingsModal');
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const provider = document.getElementById('providerSelect').value;
    const apiKey = document.getElementById('apiKeyInput').value;

    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, api_key: apiKey })
      });
      const data = await res.json();
      if (data.success) {
        closeModal('settingsModal');
        fetchStatus();
      }
    } catch (err) {
      console.error(err);
      alert('Error updating settings');
    }
  });
}

async function fetchStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    const statusText = document.getElementById('engineStatusText');
    if (data.has_live_key) {
      statusText.textContent = `AI Engine: Live ${data.provider.toUpperCase()}`;
    } else {
      statusText.textContent = 'AI Engine: Local Semantic / Ready';
    }
  } catch (err) {
    console.error(err);
  }
}
