/**
 * reports.js — Load/generate/delete reports, templates.
 */
(function (App) {
    'use strict';

    function _opTypeFromName(name) {
        const n = name.toLowerCase();
        if (n.includes('appeal') || n.includes('step4')) return { label: 'Appeal',   icon: 'fa-gavel',     color: '#f59e0b' };
        if (n.includes('health'))                         return { label: 'Health',   icon: 'fa-heartbeat', color: '#22c55e' };
        if (n.includes('step1'))                          return { label: 'Step 1',   icon: 'fa-cog',       color: '#60a5fa' };
        if (n.includes('step2'))                          return { label: 'Step 2',   icon: 'fa-shield-alt',color: '#a78bfa' };
        if (n.includes('step3') || n.includes('review'))  return { label: 'Review',   icon: 'fa-star',      color: '#f472b6' };
        if (n.includes('login') || n.includes('batch'))   return { label: 'Login',    icon: 'fa-sign-in-alt',color: '#34d399'};
        if (n.includes('profile'))                        return { label: 'Profiles', icon: 'fa-users',     color: '#60a5fa' };
        return { label: 'Report', icon: 'fa-file-excel', color: '#94a3b8' };
    }

    App.loadReports = async function () {
        if (!App.state.serverOnline) return;
        const rList = document.getElementById('reportsList');
        if (!rList) return;
        rList.innerHTML = '<div style="color:#64748b;font-style:italic;padding:20px 0;">Loading...</div>';

        try {
            const res = await App.apiFetch('/api/reports');
            const data = await res.json();

            if (data.success && data.reports.length > 0) {
                rList.innerHTML = '';
                data.reports.forEach(report => {
                    const date = new Date(report.modified * 1000).toLocaleString();
                    const kb = report.size >= 1024 * 1024
                        ? (report.size / 1024 / 1024).toFixed(1) + ' MB'
                        : (report.size / 1024).toFixed(1) + ' KB';
                    const isMN = report.type === 'mailnexus';
                    const op = _opTypeFromName(report.name);

                    const d = document.createElement('div');
                    d.className = 'report-item';
                    d.innerHTML = `
                        <div class="report-info" style="flex:1;min-width:0;">
                            <div class="report-title" style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                                <span style="display:inline-flex;align-items:center;gap:4px;background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.1);border-radius:4px;padding:1px 7px;font-size:10px;font-weight:700;color:${op.color};white-space:nowrap;">
                                    <i class="fas ${op.icon}"></i> ${op.label}
                                </span>
                                ${isMN ? '<span class="report-badge badge-pro">PRO</span>' : '<span class="report-badge badge-raw">RAW</span>'}
                                <span style="font-size:13px;font-weight:600;color:#e2e8f0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${App.escapeHtml(report.name)}</span>
                            </div>
                            <div class="report-meta" style="margin-top:4px;">
                                <span>${kb}</span>
                                <span style="margin:0 6px;color:#334155;">|</span>
                                <span>${date}</span>
                            </div>
                        </div>
                        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
                            <div class="report-action report-open-btn" title="Open in Excel">
                                <i class="fas fa-external-link-alt"></i> Open
                            </div>
                            <div class="report-action report-delete-btn" title="Delete" style="color:#f87171;">
                                <i class="fas fa-trash"></i>
                            </div>
                        </div>`;

                    d.querySelector('.report-open-btn').onclick = (e) => {
                        e.stopPropagation();
                        if (window.electronAPI && window.electronAPI.openPath) {
                            window.electronAPI.openPath(report.path);
                        }
                    };

                    d.querySelector('.report-delete-btn').onclick = (e) => {
                        e.stopPropagation();
                        _deleteSingleReport(report.path, report.name);
                    };

                    rList.appendChild(d);
                });
            } else {
                rList.innerHTML = '<div style="color:#64748b;font-style:italic;padding:20px 0;">No reports yet. Generate one above.</div>';
            }
        } catch (e) {
            rList.innerHTML = '<div style="color:#f87171;">Error loading reports. Is the server running?</div>';
        }
    };

    // Generate report for a specific source type
    async function _generateReport(source, btn) {
        if (!App.state.serverOnline) { App.toast('Server offline', 'error'); return; }
        const origHTML = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        btn.disabled = true;

        const payload = { source };
        if (['step1','step2','step3','step4'].includes(source)) {
            payload.step = source;
            payload.source = '';
        }

        try {
            const res = await App.apiFetch('/api/reports/generate', {
                method: 'POST', body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                btn.innerHTML = '<i class="fas fa-check"></i> Done';
                App.toast(data.message || 'Report generated', 'success');
                App.loadReports();
            } else {
                App.toast(data.message || 'Generation failed', 'error');
                btn.innerHTML = origHTML;
            }
        } catch (e) {
            App.toast('Error generating report', 'error');
            btn.innerHTML = origHTML;
        }
        btn.disabled = false;
        setTimeout(() => { btn.innerHTML = origHTML; }, 2500);
    }

    async function _deleteSingleReport(filePath, fileName) {
        if (!confirm(`Delete "${fileName}"?`)) return;
        try {
            const res = await App.apiFetch('/api/reports/single', {
                method: 'DELETE', body: JSON.stringify({ path: filePath })
            });
            const data = await res.json();
            if (data.success) { App.toast(`Deleted: ${fileName}`, 'success'); App.loadReports(); }
            else App.toast('Delete failed: ' + data.message, 'error');
        } catch (e) { App.toast('Delete error', 'error'); }
    }

    async function _generateTemplate() {
        if (!App.state.serverOnline) return alert('Server not running.');
        const stepSelect = document.getElementById('templateStepSelect');
        const btn = document.getElementById('generateTemplateBtn');
        if (!stepSelect || !btn) return;

        const step = stepSelect.value;
        const origHTML = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        btn.disabled = true;

        try {
            const res = await App.apiFetch('/api/template/generate', {
                method: 'POST', body: JSON.stringify({ step: parseInt(step) })
            });
            const data = await res.json();
            if (data.success) {
                btn.innerHTML = '<i class="fas fa-check"></i> Done';
                App.toast('Template generated', 'success');
                if (window.electronAPI && window.electronAPI.openPath) window.electronAPI.openPath(data.template_path);
            } else {
                App.toast('Failed: ' + data.message, 'error');
                btn.innerHTML = origHTML;
            }
        } catch (e) {
            App.toast('Error: ' + e.message, 'error');
            btn.innerHTML = origHTML;
        }
        btn.disabled = false;
        setTimeout(() => { btn.innerHTML = origHTML; }, 2500);
    }

    App.setupGenerateReport = function () {
        // Wire individual generate buttons on the report cards
        document.querySelectorAll('.rpt-gen-btn').forEach(btn => {
            btn.addEventListener('click', () => _generateReport(btn.dataset.source, btn));
        });

        const refreshBtn = document.getElementById('refreshReportsBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', () => App.loadReports());
    };

    App.setupDeleteAllReports = function () {
        const btn = document.getElementById('deleteAllReportsBtn');
        if (!btn) return;
        btn.addEventListener('click', async () => {
            if (!confirm('Delete ALL reports? This cannot be undone.')) return;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            try {
                const res = await App.apiFetch('/api/reports/all', { method: 'DELETE' });
                const data = await res.json();
                if (data.success) {
                    App.toast(`Deleted ${data.deleted} report(s)`, 'success');
                    App.loadReports();
                } else App.toast('Delete failed', 'error');
            } catch (e) { App.toast('Delete error', 'error'); }
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-trash-alt"></i> Delete All';
        });
    };

    App.setupGenerateTemplate = function () {
        const btn = document.getElementById('generateTemplateBtn');
        if (btn) btn.addEventListener('click', _generateTemplate);
    };

})(window.App || (window.App = {}));
