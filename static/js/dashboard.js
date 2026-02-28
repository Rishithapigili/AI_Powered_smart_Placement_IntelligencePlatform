/* ─── Dashboard JS ─── */
const API = '';
const token = () => localStorage.getItem('access_token');
const headers = () => ({ 'Content-Type': 'application/json', 'Authorization': `Bearer ${token()}` });
let currentRole = '';
let currentUserId = null;

// ─── Init ───
document.addEventListener('DOMContentLoaded', async () => {
    if (!token()) { window.location.href = '/'; return; }
    try {
        const res = await fetch(`${API}/api/auth/me`, { headers: headers() });
        if (!res.ok) throw new Error();
        const user = await res.json();
        currentRole = user.role.toLowerCase();
        currentUserId = user.id;
        console.log("Logged in as:", currentRole, currentUserId);
        document.getElementById('username-display').textContent = user.username;
        document.getElementById('role-badge').textContent = user.role;
        document.getElementById('role-badge').className = `role-badge ${currentRole}`;
        setupNav();
    } catch (e) {
        console.error("Init Error:", e);
        localStorage.clear();
        window.location.href = '/';
    }
});

// ─── Navigation ───
function setupNav() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        const itemRole = item.dataset.role ? item.dataset.role.toLowerCase() : 'all';
        if (itemRole !== 'all' && itemRole !== currentRole) {
            item.style.display = 'none';
        } else {
            item.style.display = 'flex';
            item.onclick = () => {
                console.log("Navigating to:", item.dataset.panel);
                navItems.forEach(n => n.classList.remove('active'));
                item.classList.add('active');
                showPanel(item.dataset.panel);
            };
        }
    });

    const firstVisible = document.querySelector(`.nav-item[data-role="${currentRole}"], .nav-item[data-role="all"]`);
    if (firstVisible && firstVisible.style.display !== 'none') {
        firstVisible.classList.add('active');
        showPanel(firstVisible.dataset.panel);
    }
}

function showPanel(panelId) {
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    const panel = document.getElementById(panelId);
    if (panel) { panel.classList.add('active'); }
    // Load data
    if (panelId === 'panel-dashboard') loadDashboard();
    if (panelId === 'panel-metrics') loadAdminMetrics();
    if (panelId === 'panel-users') loadUsers();
    if (panelId === 'panel-students') loadStudents();
    if (panelId === 'panel-placements') loadPlacements();
    if (panelId === 'panel-profile') loadMyProfile();
    if (panelId === 'panel-my-placements') loadMyPlacements();
    if (panelId === 'panel-my-status') loadMyStatus();
    if (panelId === 'panel-my-prediction') loadMyPrediction();
    if (panelId === 'panel-my-evaluation') loadMyEvaluation();
    if (panelId === 'panel-browse') loadBrowseStudents();
    if (panelId === 'panel-company-placements') loadCompanyPlacements();
    if (panelId === 'panel-company-reports') loadCompanyReports();
}

// ─── Toast ───
function showToast(msg, type = 'success') {
    const t = document.createElement('div');
    t.className = `toast toast-${type}`;
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3000);
}

// ─── API helper ───
async function api(url, method = 'GET', body = null) {
    const opts = { method, headers: headers() };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API}${url}`, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Request failed');
    return data;
}

// ─── Logout ───
function logout() {
    console.log("Logging out...");
    localStorage.removeItem('access_token');
    localStorage.clear();
    window.location.replace('/');
}

// ═══════════════ ADMIN ═══════════════

// Dashboard overview
async function loadDashboard() {
    try {
        const users = await api('/api/admin/users');
        const students = await api('/api/admin/students');
        const placements = await api('/api/admin/placements');
        document.getElementById('stat-total-users').textContent = users.length;
        document.getElementById('stat-total-students').textContent = students.length;
        document.getElementById('stat-verified').textContent = students.filter(s => s.is_verified).length;
        document.getElementById('stat-placed').textContent = students.filter(s => s.placement_status === 'placed').length;
        document.getElementById('stat-opportunities').textContent = placements.length;
        const avgScore = students.length ? (students.reduce((a, s) => a + s.employability_score, 0) / students.length).toFixed(1) : 0;
        document.getElementById('stat-avg-score').textContent = avgScore;
    } catch { }
}

// ML Evaluation Metrics (Admin)
async function loadAdminMetrics() {
    try {
        const metrics = await api('/api/ml/metrics');

        const acc = metrics.classifier_accuracy || 0;
        document.getElementById('metric-accuracy').textContent = acc + '%';
        const navAcc = document.getElementById('nav-metric-acc');
        if (navAcc) navAcc.textContent = acc + '%';

        // Precision, Recall, F1 for the 'Placed' Class
        const placedReport = metrics.classifier_report?.placed || {};
        const precision = placedReport.precision || 0;
        const recall = placedReport.recall || 0;
        const f1 = placedReport['f1-score'] || 0;

        document.getElementById('metric-precision').textContent = precision.toFixed(2);
        document.getElementById('metric-recall').textContent = recall.toFixed(2);
        document.getElementById('metric-f1').textContent = f1.toFixed(2);

        const navPre = document.getElementById('nav-metric-pre');
        if (navPre) navPre.textContent = precision.toFixed(2);
        const navRec = document.getElementById('nav-metric-rec');
        if (navRec) navRec.textContent = recall.toFixed(2);
        const navF1 = document.getElementById('nav-metric-f1');
        if (navF1) navF1.textContent = f1.toFixed(2);

        const navMetrics = document.querySelector('.nav-metrics');
        if (navMetrics) navMetrics.style.display = 'block';

    } catch (e) {
        showToast("Error loading Evaluation Metrics: " + e.message, 'error');
    }
}

// Users management
async function loadUsers() {
    try {
        const users = await api('/api/admin/users');
        const tbody = document.getElementById('users-tbody');
        tbody.innerHTML = users.map(u => `
            <tr>
                <td>${u.id}</td><td>${u.username}</td><td>${u.email}</td>
                <td><span class="badge badge-purple">${u.role}</span></td>
                <td>${u.is_active ? '<span class="badge badge-green">Active</span>' : '<span class="badge badge-red">Inactive</span>'}</td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="editUserModal(${u.id})">Edit</button>
                    ${u.role !== 'admin' ? `<button class="btn btn-sm btn-danger" onclick="deactivateUser(${u.id})">Deactivate</button>` : ''}
                </td>
            </tr>
        `).join('');
    } catch (e) { showToast(e.message, 'error'); }
}

function openCreateUserModal() {
    document.getElementById('modal-user-title').textContent = 'Create User';
    document.getElementById('user-form').reset();
    document.getElementById('user-id-field').value = '';
    document.getElementById('user-password').required = true;
    document.getElementById('modal-user').classList.add('active');
}

async function editUserModal(id) {
    try {
        const users = await api('/api/admin/users');
        const u = users.find(x => x.id === id);
        if (!u) return;
        document.getElementById('modal-user-title').textContent = 'Edit User';
        document.getElementById('user-id-field').value = u.id;
        document.getElementById('user-username').value = u.username;
        document.getElementById('user-email').value = u.email;
        document.getElementById('user-role').value = u.role;
        document.getElementById('user-password').value = '';
        document.getElementById('user-password').required = false;
        document.getElementById('modal-user').classList.add('active');
    } catch (e) { showToast(e.message, 'error'); }
}

async function saveUser(e) {
    e.preventDefault();
    const id = document.getElementById('user-id-field').value;
    const body = {
        username: document.getElementById('user-username').value,
        email: document.getElementById('user-email').value,
        role: document.getElementById('user-role').value,
    };
    const pw = document.getElementById('user-password').value;
    if (pw) body.password = pw;
    try {
        if (id) { await api(`/api/admin/users/${id}`, 'PUT', body); }
        else { body.password = pw; await api('/api/admin/users', 'POST', body); }
        closeModal('modal-user');
        showToast(id ? 'User updated' : 'User created');
        loadUsers();
    } catch (e) { showToast(e.message, 'error'); }
}

async function deactivateUser(id) {
    if (!confirm('Deactivate this user?')) return;
    try { await api(`/api/admin/users/${id}`, 'DELETE'); showToast('User deactivated'); loadUsers(); }
    catch (e) { showToast(e.message, 'error'); }
}

// Students management
async function loadStudents() {
    const dept = document.getElementById('filter-dept')?.value || '';
    const cgpa = document.getElementById('filter-cgpa')?.value || '';
    const skills = document.getElementById('filter-skills')?.value || '';
    let url = '/api/admin/students?';
    if (dept) url += `department=${encodeURIComponent(dept)}&`;
    if (cgpa) url += `min_cgpa=${cgpa}&`;
    if (skills) url += `skills=${encodeURIComponent(skills)}&`;
    try {
        const students = await api(url);
        const tbody = document.getElementById('students-tbody');
        tbody.innerHTML = students.map(s => `
            <tr>
                <td>${s.roll_number || '-'}</td><td>${s.full_name}</td><td>${s.department || '-'}</td>
                <td>${s.cgpa}</td><td>${s.employability_score}</td>
                <td>${s.is_verified ? '<span class="badge badge-green">Verified</span>' : '<span class="badge badge-orange">Pending</span>'}</td>
                <td><span class="badge ${s.placement_status === 'placed' ? 'badge-green' : s.placement_status === 'shortlisted' ? 'badge-orange' : 'badge-red'}">${s.placement_status}</span></td>
                <td>
                    <button class="btn btn-sm btn-success" onclick="toggleVerify(${s.id})">${s.is_verified ? 'Unverify' : 'Verify'}</button>
                    <button class="btn btn-sm btn-outline" onclick="viewStudentDetail(${s.id})">View</button>
                </td>
            </tr>
        `).join('');
    } catch (e) { showToast(e.message, 'error'); }
}

async function toggleVerify(id) {
    try { await api(`/api/admin/students/${id}/verify`, 'PUT'); showToast('Verification toggled'); loadStudents(); }
    catch (e) { showToast(e.message, 'error'); }
}

async function viewStudentDetail(id) {
    try {
        const s = await api(`/api/admin/students/${id}`);
        let html = `<p><strong>Name:</strong> ${s.full_name}</p><p><strong>Dept:</strong> ${s.department}</p>
            <p><strong>Roll:</strong> ${s.roll_number || '-'}</p><p><strong>CGPA:</strong> ${s.cgpa}</p>
            <p><strong>10th:</strong> ${s.tenth_percentage}% | <strong>12th:</strong> ${s.twelfth_percentage}%</p>
            <p><strong>Skills:</strong> ${(s.skills || []).join(', ') || 'None'}</p>
            <p><strong>Certifications:</strong> ${(s.certifications || []).join(', ') || 'None'}</p>
            <p><strong>Projects:</strong> ${(s.projects || []).join(', ') || 'None'}</p>
            <p><strong>Internships:</strong> ${s.internship_count}</p>
            <p><strong>Score:</strong> ${s.employability_score}</p>
            <p><strong>Status:</strong> ${s.placement_status}</p>`;
        document.getElementById('student-detail-content').innerHTML = html;
        document.getElementById('modal-student-detail').classList.add('active');
    } catch (e) { showToast(e.message, 'error'); }
}

async function downloadReport(format) {
    const h = { 'Authorization': `Bearer ${token()}` };
    const url = format === 'pdf' ? '/api/admin/reports/pdf' : '/api/admin/reports';
    const res = await fetch(`${API}${url}`, { headers: h });
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = format === 'pdf' ? 'report.pdf' : 'report.csv';
    a.click();
}

async function recalculateScores() {
    try { const d = await api('/api/admin/recalculate-scores', 'POST'); showToast(d.message); }
    catch (e) { showToast(e.message, 'error'); }
}

// Placements
async function loadPlacements() {
    try {
        const opps = await api('/api/admin/placements');
        const tbody = document.getElementById('placements-tbody');
        tbody.innerHTML = opps.map(o => `
            <tr>
                <td>${o.company_name}</td><td>${o.role_title}</td><td>${o.package || '-'}</td>
                <td>${o.min_cgpa}</td><td>${o.deadline ? new Date(o.deadline).toLocaleDateString() : '-'}</td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="editPlacementModal(${o.id})">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deletePlacement(${o.id})">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (e) { showToast(e.message, 'error'); }
}

function openCreatePlacementModal() {
    document.getElementById('modal-placement-title').textContent = 'Create Opportunity';
    document.getElementById('placement-form').reset();
    document.getElementById('placement-id-field').value = '';
    document.getElementById('modal-placement').classList.add('active');
}

async function editPlacementModal(id) {
    try {
        const endpoint = currentRole === 'admin' ? '/api/admin/placements' : '/api/company/placements';
        const opps = await api(endpoint);
        const o = opps.find(x => x.id === id);
        if (!o) return;
        document.getElementById('modal-placement-title').textContent = 'Edit Opportunity';
        document.getElementById('placement-id-field').value = o.id;
        document.getElementById('pl-company').value = o.company_name;
        document.getElementById('pl-role').value = o.role_title;
        document.getElementById('pl-package').value = o.package;
        document.getElementById('pl-cgpa').value = o.min_cgpa;
        document.getElementById('pl-eligibility').value = o.eligibility_criteria;
        document.getElementById('pl-skills').value = (o.required_skills || []).join(', ');
        document.getElementById('pl-deadline').value = o.deadline ? o.deadline.split('T')[0] : '';
        document.getElementById('modal-placement').classList.add('active');
    } catch (e) { showToast(e.message, 'error'); }
}

async function savePlacement(e) {
    e.preventDefault();
    const id = document.getElementById('placement-id-field').value;
    const body = {
        company_name: document.getElementById('pl-company').value,
        role_title: document.getElementById('pl-role').value,
        package: document.getElementById('pl-package').value,
        min_cgpa: parseFloat(document.getElementById('pl-cgpa').value) || 0,
        eligibility_criteria: document.getElementById('pl-eligibility').value,
        required_skills: document.getElementById('pl-skills').value.split(',').map(s => s.trim()).filter(Boolean),
        deadline: document.getElementById('pl-deadline').value || null,
    };
    try {
        const baseEndpoint = currentRole === 'admin' ? '/api/admin/placements' : '/api/company/placements';
        if (id) { await api(`${baseEndpoint}/${id}`, 'PUT', body); }
        else { await api(baseEndpoint, 'POST', body); }
        closeModal('modal-placement');
        showToast(id ? 'Opportunity updated' : 'Opportunity created');

        if (currentRole === 'admin') loadPlacements();
        else if (currentRole === 'company') loadCompanyPlacements();

    } catch (e) { showToast(e.message, 'error'); }
}

async function deletePlacement(id) {
    if (!confirm('Delete this opportunity?')) return;
    try {
        const baseEndpoint = currentRole === 'admin' ? '/api/admin/placements' : '/api/company/placements';
        await api(`${baseEndpoint}/${id}`, 'DELETE');
        showToast('Deleted');

        if (currentRole === 'admin') loadPlacements();
        else if (currentRole === 'company') loadCompanyPlacements();

    } catch (e) { showToast(e.message, 'error'); }
}

// ═══════════════ STUDENT ═══════════════

async function loadMyProfile() {
    try {
        const p = await api('/api/student/profile');
        document.getElementById('sp-fullname').value = p.full_name;
        document.getElementById('sp-dept').value = p.department;
        document.getElementById('sp-roll').value = p.roll_number || '';
        document.getElementById('sp-cgpa').value = p.cgpa;
        document.getElementById('sp-10th').value = p.tenth_percentage;
        document.getElementById('sp-12th').value = p.twelfth_percentage;
        // Skills dropdowns — skills array stores [tech_category, soft_category]
        const skills = p.skills || [];
        document.getElementById('sp-prog-rating').value = skills[0] || '';
        document.getElementById('sp-soft-rating').value = skills[1] || '';
        document.getElementById('sp-certs').value = (p.certifications || []).join(', ');
        document.getElementById('sp-projects').value = (p.projects || []).join(', ');
        document.getElementById('sp-internships').value = (p.internships || []).join(', ');
        document.getElementById('sp-intern-count').value = p.internship_count;
        document.getElementById('sp-career').value = p.career_preferences;
        // Score
        const score = p.employability_score || 0;
        document.getElementById('my-score-value').textContent = score;
        drawScoreRing(score);
        // Status badges
        document.getElementById('my-verified').innerHTML = p.is_verified ? '<span class="badge badge-green">Verified</span>' : '<span class="badge badge-orange">Pending Verification</span>';
        document.getElementById('my-placement-status').innerHTML = `<span class="badge ${p.placement_status === 'placed' ? 'badge-green' : 'badge-orange'}">${p.placement_status}</span>`;
    } catch (e) { showToast(e.message, 'error'); }
}

function drawScoreRing(score) {
    const ring = document.getElementById('score-ring-svg');
    if (!ring) return;
    const pct = score / 100;
    const circumference = 2 * Math.PI * 42;
    const offset = circumference * (1 - pct);
    ring.querySelector('.ring-fill').style.strokeDasharray = circumference;
    ring.querySelector('.ring-fill').style.strokeDashoffset = offset;
}

async function saveMyProfile(e) {
    e.preventDefault();
    // Map skill names to numeric ratings
    const techSkillMap = {
        'Python & Data Analysis': 8, 'Full Stack Development': 9, 'Cloud Computing': 7,
        'Cybersecurity': 8, 'AI & Machine Learning': 10, 'Mobile App Development': 7,
        'DevOps Engineering': 8, 'Database Management': 6, 'Business Intelligence': 6, 'Embedded Systems': 7
    };
    const softSkillMap = {
        'Leadership & Teamwork': 9, 'Critical Thinking': 8, 'Effective Communication': 8,
        'Adaptability': 7, 'Problem Solving': 9, 'Time Management': 7,
        'Creativity': 8, 'Decision Making': 7, 'Emotional Intelligence': 6, 'Collaboration': 8
    };
    const techVal = document.getElementById('sp-prog-rating').value;
    const softVal = document.getElementById('sp-soft-rating').value;

    const body = {
        full_name: document.getElementById('sp-fullname').value,
        department: document.getElementById('sp-dept').value,
        roll_number: document.getElementById('sp-roll').value,
        cgpa: parseFloat(document.getElementById('sp-cgpa').value) || 0,
        tenth_percentage: parseFloat(document.getElementById('sp-10th').value) || 0,
        twelfth_percentage: parseFloat(document.getElementById('sp-12th').value) || 0,
        programming_skills_rating: techSkillMap[techVal] || 5,
        soft_skills_rating: softSkillMap[softVal] || 5,
        skills: [techVal, softVal].filter(Boolean),
        certifications: document.getElementById('sp-certs').value.split(',').map(s => s.trim()).filter(Boolean),
        projects: document.getElementById('sp-projects').value.split(',').map(s => s.trim()).filter(Boolean),
        internships: document.getElementById('sp-internships').value.split(',').map(s => s.trim()).filter(Boolean),
        internship_count: parseInt(document.getElementById('sp-intern-count').value) || 0,
        career_preferences: document.getElementById('sp-career').value,
    };
    try { const d = await api('/api/student/profile', 'PUT', body); showToast('Profile updated! Score: ' + d.profile.employability_score); loadMyProfile(); }
    catch (e) { showToast(e.message, 'error'); }
}

async function uploadFile(type) {
    const input = document.getElementById(`upload-${type}`);
    if (!input.files.length) return;
    const fd = new FormData();
    fd.append('file', input.files[0]);
    try {
        const res = await fetch(`${API}/api/student/upload/${type}`, { method: 'POST', headers: { 'Authorization': `Bearer ${token()}` }, body: fd });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);
        showToast(`${type} uploaded`);
        input.value = '';
    } catch (e) { showToast(e.message, 'error'); }
}

async function loadMyPlacements() {
    try {
        const opps = await api('/api/student/placements');
        const tbody = document.getElementById('my-placements-tbody');
        tbody.innerHTML = opps.map(o => `
            <tr>
                <td>${o.company_name}</td><td>${o.role_title}</td><td>${o.package || '-'}</td>
                <td>${o.min_cgpa}</td><td>${o.deadline ? new Date(o.deadline).toLocaleDateString() : '-'}</td>
                <td>${o.applied_status ? `<span style="color: #ffcc00; font-weight: 600;">Applied</span>` : `<button class="btn btn-sm btn-primary" onclick="applyPlacement(${o.id})">Apply</button>`}</td>
            </tr>
        `).join('');
    } catch (e) { showToast(e.message, 'error'); }
}

async function applyPlacement(id) {
    try {
        await api(`/api/student/placements/${id}/apply`, 'POST');
        showToast('Application submitted!');
        loadMyPlacements();
    }
    catch (e) { showToast(e.message, 'error'); }
}

async function loadMyStatus() {
    try {
        const data = await api('/api/student/status');
        document.getElementById('overall-status').textContent =
            data.placement_status === 'placed' ? `🎉 Placed at ${data.placement_company}` : 'Not Placed Yet';

        let html = '';
        data.applications.forEach(app => {
            const date = new Date(app.applied_at).toLocaleDateString();
            const badgeClass = {
                'applied': 'badge-purple',
                'shortlisted': 'badge-orange',
                'selected': 'badge-green',
                'rejected': 'badge-red'
            }[app.status.toLowerCase()] || 'badge-purple';

            html += `<tr>
                <td>${app.company_name}</td>
                <td>${app.role_title}</td>
                <td>
                    <span class="badge ${badgeClass}">${app.status.toUpperCase()}</span>
                </td>
                <td>${date}</td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="viewApplicationFlow(${app.id})">🔍 View Flow</button>
                </td>
            </tr>`;
        });
        document.getElementById('my-apps-tbody').innerHTML = html;
    } catch (e) { showToast(e.message, 'error'); }
}

async function viewApplicationFlow(recordId) {
    try {
        const data = await api(`/api/student/applications/${recordId}/flow`);

        let flowHtml = `<div class="flow-container">`;

        data.flow.forEach(stage => {
            let dotClass = 'future';
            if (stage.active) {
                dotClass = 'active'; // Current stage
            } else if (stage.completed) {
                dotClass = 'completed'; // Completed/past stage
            }

            let icon = '⏱️';
            if (stage.stage === 'Applied') icon = '📄';
            if (stage.stage === 'Shortlisted') icon = '⭐';
            if (stage.stage === 'Selected') icon = '🎉';
            if (stage.stage === 'Rejected') icon = '❌';

            flowHtml += `
                <div class="flow-step ${dotClass}">
                    <div class="flow-line"></div>
                    <div class="flow-dot ${dotClass}">${stage.completed ? icon : ''}</div>
                    <div class="flow-content">
                        <div class="flow-title">${stage.stage}</div>
                        ${stage.active ? `<div style="font-size:12px;color:var(--text-secondary);margin-top:4px;">Current Status</div>` : ''}
                    </div>
                </div>
            `;
        });

        flowHtml += `</div>`;
        document.getElementById('app-flow-content').innerHTML = flowHtml;
        openModal('modal-app-flow');
    } catch (e) { showToast(e.message, 'error'); }
}

// ═══════════════ COMPANY ═══════════════

async function loadBrowseStudents() {
    const dept = document.getElementById('c-filter-dept')?.value || '';
    const cgpa = document.getElementById('c-filter-cgpa')?.value || '';
    const skills = document.getElementById('c-filter-skills')?.value || '';
    let url = '/api/company/students?';
    if (dept) url += `department=${encodeURIComponent(dept)}&`;
    if (cgpa) url += `min_cgpa=${cgpa}&`;
    if (skills) url += `skills=${encodeURIComponent(skills)}&`;
    try {
        const students = await api(url);
        const tbody = document.getElementById('browse-tbody');
        tbody.innerHTML = students.map(s => `
            <tr>
                <td>${s.full_name}</td><td>${s.department || '-'}</td><td>${s.cgpa}</td>
                <td>${(s.skills || []).slice(0, 3).join(', ')}</td><td>${s.employability_score}</td>
                <td><span class="badge ${s.placement_status === 'placed' ? 'badge-green' : 'badge-orange'}">${s.placement_status}</span></td>
            </tr>
        `).join('');
    } catch (e) { showToast(e.message, 'error'); }
}

async function findAIMatches() {
    const skillsText = document.getElementById('c-ai-skills').value;
    if (!skillsText.trim()) {
        showToast('Please enter some skills to search for.', 'error');
        return;
    }

    try {
        const data = await api('/api/ml/recommend', 'POST', { skills: skillsText, top_n: 10 });
        const container = document.getElementById('ai-matches-container');
        const tbody = document.getElementById('ai-matches-tbody');

        if (data.recommendations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No strong matches found.</td></tr>';
        } else {
            tbody.innerHTML = data.recommendations.map(s => `
                <tr>
                    <td><strong>${s.full_name}</strong><br><small style="color:var(--text-secondary);">${s.department || ''}</small></td>
                    <td>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span>${s.match_percentage}%</span>
                            <div style="width:60px; height:6px; background:rgba(255,255,255,0.1); border-radius:3px;">
                                <div style="width:${s.match_percentage}%; height:100%; background:var(--accent); border-radius:3px;"></div>
                            </div>
                        </div>
                    </td>
                    <td style="font-size:13px;">${(s.skills || []).join(', ')}</td>
                    <td>${s.cgpa}</td>
                    <td><span class="badge ${s.placement_status === 'placed' ? 'badge-green' : 'badge-orange'}">${s.placement_status}</span></td>
                </tr>
            `).join('');
        }

        container.style.display = 'block';
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function loadCompanyReports() {
    try {
        const data = await api('/api/company/reports');
        document.getElementById('cr-total').textContent = data.total_students;
        document.getElementById('cr-avg-cgpa').textContent = data.average_cgpa;
        document.getElementById('cr-avg-score').textContent = data.average_score;
        const deptList = document.getElementById('cr-depts');
        deptList.innerHTML = Object.entries(data.department_breakdown || {}).map(([d, c]) => `<tr><td>${d}</td><td>${c}</td></tr>`).join('');
    } catch (e) { showToast(e.message, 'error'); }
}

async function loadCompanyPlacements() {
    try {
        const opps = await api('/api/company/placements');
        const tbody = document.getElementById('company-placements-tbody');
        tbody.innerHTML = opps.map(o => `
            <tr>
                <td>${o.role_title}</td><td>${o.package || '-'}</td>
                <td>${o.min_cgpa}</td><td>${o.deadline ? new Date(o.deadline).toLocaleDateString() : '-'}</td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="viewOpportunityApplications(${o.id})">Applications</button>
                    <button class="btn btn-sm btn-outline" onclick="editPlacementModal(${o.id})">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deletePlacement(${o.id})">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (e) { showToast(e.message, 'error'); }
}

async function viewOpportunityApplications(oppId) {
    try {
        const apps = await api(`/api/admin/placements/${oppId}/records`);
        if (!apps || apps.length === 0) {
            showToast('No applications found for this opportunity.');
            return;
        }

        let html = `
            <table style="width:100%; text-align:left; border-collapse:collapse; margin-top:16px;">
                <thead>
                    <tr style="border-bottom:1px solid var(--border-glass);">
                        <th style="padding:8px;">Student</th>
                        <th style="padding:8px;">Status</th>
                        <th style="padding:8px;">Actions</th>
                    </tr>
                </thead>
                <tbody>
        `;

        apps.forEach(a => {
            const badgeClass = {
                'applied': 'badge-purple',
                'shortlisted': 'badge-orange',
                'selected': 'badge-green',
                'rejected': 'badge-red'
            }[a.status.toLowerCase()] || 'badge-purple';

            html += `
                <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                    <td style="padding:12px 8px;">${a.student_name}</td>
                    <td style="padding:12px 8px;">
                        <span class="badge ${badgeClass}">${a.status.toUpperCase()}</span>
                    </td>
                    <td style="padding:12px 8px;">
                        <button class="btn btn-sm btn-primary" onclick="openUpdateStatusModal(${a.id}, '${a.status}')">Update Status</button>
                    </td>
                </tr>
            `;
        });

        html += `</tbody></table>`;
        document.getElementById('student-detail-content').innerHTML = `
            <h4 style="margin-bottom:12px;">Applications</h4>
            ${html}
        `;
        openModal('modal-student-detail');
    } catch (e) { showToast(e.message, 'error'); }
}

function openUpdateStatusModal(recordId, currentStatus) {
    document.getElementById('us-record-id').value = recordId;
    document.getElementById('us-status-select').value = currentStatus.toLowerCase();
    openModal('modal-update-status');
}

async function submitUpdateStatus(e) {
    e.preventDefault();
    const recordId = document.getElementById('us-record-id').value;
    const newStatus = document.getElementById('us-status-select').value;

    try {
        await api(`/api/company/applications/${recordId}/status`, 'PUT', { status: newStatus });
        showToast(`Status updated to ${newStatus}`);
        closeModal('modal-update-status');
        closeModal('modal-student-detail'); // Just close it to avoid complex state management
        // Ideally we would refresh the applications list here, but closing is simple enough
    } catch (e) { showToast(e.message, 'error'); }
}

// ─── Modal helpers ───
function closeModal(id) { document.getElementById(id).classList.remove('active'); }

// ═══════════════ ML PREDICTIONS ═══════════════

async function findAIMatches() {
    const skills = document.getElementById('c-ai-skills').value.trim();
    if (!skills) return showToast('Please enter role or skills to match', 'error');

    try {
        const data = await api('/api/ml/recommend', 'POST', { skills: skills, top_n: 5 });
        const container = document.getElementById('ai-matches-container');
        const tbody = document.getElementById('ai-matches-tbody');

        if (!data.recommendations || data.recommendations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No direct matches found.</td></tr>';
        } else {
            tbody.innerHTML = data.recommendations.map(r => `
                <tr>
                    <td style="font-weight:600;">${r.name}</td>
                    <td><span class="badge ${r.similarity_score > 0.6 ? 'badge-green' : 'badge-orange'}">${Math.round(r.similarity_score * 100)}%</span></td>
                    <td style="font-size:12px; max-width:200px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${r.skills.join(', ')}">${r.skills.join(', ')}</td>
                    <td>${r.cgpa.toFixed(2)}</td>
                    <td><span class="badge ${r.placement_status === 'placed' ? 'badge-green' : 'badge-purple'}">${r.placement_status.toUpperCase()}</span></td>
                </tr>
            `).join('');
        }

        container.style.display = 'block';
    } catch (e) { showToast(e.message, 'error'); }
}// Student: load prediction for own profile
async function loadMyPrediction() {
    try {
        const data = await api('/api/ml/predict/my-profile');
        if (!data || !data.profile_features) throw new Error("Could not load profile features for prediction.");

        const pf = data.profile_features;
        const pr = data.placement_prediction;
        const sr = data.salary_prediction;

        // Update features table
        if (document.getElementById('myml-cgpa')) document.getElementById('myml-cgpa').textContent = pf.cgpa || '0';
        if (document.getElementById('myml-prog')) document.getElementById('myml-prog').textContent = pf.programming_skills_rating || '0';
        if (document.getElementById('myml-soft')) document.getElementById('myml-soft').textContent = pf.soft_skills_rating || '0';
        if (document.getElementById('myml-intern')) document.getElementById('myml-intern').textContent = pf.internship_count || '0';
        if (document.getElementById('myml-certs')) document.getElementById('myml-certs').textContent = pf.certification_count || '0';

        // Placement prediction
        const statusEl = document.getElementById('myml-status');
        if (statusEl) {
            statusEl.textContent = (pr.status || 'UNKNOWN').toUpperCase();
            statusEl.style.color = pr.prediction === 1 ? 'var(--green)' : 'var(--red)';
        }

        const confEl = document.getElementById('myml-confidence');
        if (confEl) confEl.textContent = (pr.confidence || 0) + '%';

        const barEl = document.getElementById('myml-conf-bar');
        if (barEl) barEl.style.width = (pr.confidence || 0) + '%';

        // Salary prediction
        const salEl = document.getElementById('myml-salary');
        if (salEl) salEl.textContent = (sr.predicted_salary_lpa || 0).toFixed(2) + ' LPA';

        const rangeEl = document.getElementById('myml-salary-range');
        if (rangeEl && sr.salary_range) {
            rangeEl.textContent = `Range: ${sr.salary_range.min} – ${sr.salary_range.max} LPA`;
        }

        // Feature importance
        loadFeatureImportance('student-feature-bars');

    } catch (e) {
        console.error("Prediction Error:", e);
        showToast("Error loading prediction: " + e.message, 'error');
    }
}

async function loadFeatureImportance(containerId) {
    try {
        const data = await api('/api/ml/feature-importance');
        const importances = data.feature_importances;
        const container = document.getElementById(containerId);
        if (!container) return;

        // Find max value for relative scaling
        const maxVal = Math.max(...Object.values(importances));

        let html = '';
        for (const [feature, value] of Object.entries(importances)) {
            const pct = Math.round((value / maxVal) * 100);

            // map technical names to readable names
            const labels = {
                'cgpa': 'CGPA',
                'programming_skills': 'Technical Skills',
                'soft_skills': 'Soft Skills',
                'internship_count': 'Internships',
                'certifications': 'Certifications'
            };
            const label = labels[feature] || feature;

            html += `
                <div style="margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px;">
                        <span>${label}</span>
                        <span style="color: var(--text-secondary);">${(value * 100).toFixed(1)}%</span>
                    </div>
                    <div style="background: rgba(255,255,255,0.06); height: 8px; border-radius: 4px; overflow: hidden;">
                        <div style="width: ${pct}%; background: var(--accent); height: 100%; border-radius: 4px;"></div>
                    </div>
                </div>
            `;
        }
        container.innerHTML = html;
    } catch (e) { console.error('Error loading feature importances:', e); }
}

async function loadMyEvaluation() {
    try {
        // Fetch CGPA Graph
        const cgpaRes = await fetch(`${API}/api/student/evaluation/cgpa`, {
            headers: { 'Authorization': `Bearer ${token()}` }
        });
        if (cgpaRes.ok) {
            const cgpaBlob = await cgpaRes.blob();
            const cgpaUrl = URL.createObjectURL(cgpaBlob);
            const cgpaImg = document.getElementById('eval-cgpa-img');
            cgpaImg.src = cgpaUrl;
            cgpaImg.style.display = 'block';
        }

        // Fetch Employability Graph
        const empRes = await fetch(`${API}/api/student/evaluation/employability`, {
            headers: { 'Authorization': `Bearer ${token()}` }
        });
        if (empRes.ok) {
            const empBlob = await empRes.blob();
            const empUrl = URL.createObjectURL(empBlob);
            const empImg = document.getElementById('eval-emp-img');
            empImg.src = empUrl;
            empImg.style.display = 'block';
        }
    } catch (e) {
        showToast("Failed to load evaluation graphs.", 'error');
        console.error(e);
    }
}
