/**
 * processing.js — Start, stop, progress polling, log stream, process buttons.
 */
(function (App) {
    'use strict';

    let logEventSource = null;
    let pollingInterval = null;

    // ── Recovery email/phone list helpers ─────────────────────────────────

    function _collectRecoveryValues(className) {
        var inputs = document.querySelectorAll('.' + className);
        var vals = [];
        inputs.forEach(function (inp) {
            var v = inp.value.trim();
            if (v) vals.push(v);
        });
        return vals.join(',');
    }

    function _addRecoveryItem(listId, className, placeholder, max) {
        var list = document.getElementById(listId);
        if (!list) return;
        var items = list.querySelectorAll('.recovery-item');
        if (items.length >= max) {
            alert('Maximum ' + max + ' allowed (Google limit).');
            return;
        }
        var div = document.createElement('div');
        div.className = 'recovery-item';
        div.innerHTML = '<input type="' + (className.includes('email') ? 'email' : 'tel') + '" placeholder="' + placeholder + '" class="' + className + '">' +
            '<button type="button" class="btn-remove-recovery" title="Remove"><i class="fas fa-times"></i></button>';
        list.appendChild(div);
        div.querySelector('.btn-remove-recovery').addEventListener('click', function () {
            div.remove();
            _updateRemoveBtns(listId);
        });
        _updateRemoveBtns(listId);
    }

    function _updateRemoveBtns(listId) {
        var list = document.getElementById(listId);
        if (!list) return;
        var items = list.querySelectorAll('.recovery-item');
        items.forEach(function (item) {
            var btn = item.querySelector('.btn-remove-recovery');
            if (btn) btn.style.display = items.length > 1 ? 'inline-block' : 'none';
        });
    }

    // Wire add buttons (called from setupProcessing)
    function _setupRecoveryLists() {
        var addEmailBtn = document.getElementById('addRecoveryEmail');
        if (addEmailBtn) {
            addEmailBtn.addEventListener('click', function () {
                _addRecoveryItem('recoveryEmailList', 'recovery-email-input', 'e.g. secure@domain.com', 10);
            });
        }
        var addPhoneBtn = document.getElementById('addRecoveryPhone');
        if (addPhoneBtn) {
            addPhoneBtn.addEventListener('click', function () {
                _addRecoveryItem('recoveryPhoneList', 'recovery-phone-input', 'e.g. +1234567890', 10);
            });
        }
        // Wire existing remove buttons
        document.querySelectorAll('#recoveryEmailList .btn-remove-recovery').forEach(function (btn) {
            btn.addEventListener('click', function () { btn.closest('.recovery-item').remove(); _updateRemoveBtns('recoveryEmailList'); });
        });
        document.querySelectorAll('#recoveryPhoneList .btn-remove-recovery').forEach(function (btn) {
            btn.addEventListener('click', function () { btn.closest('.recovery-item').remove(); _updateRemoveBtns('recoveryPhoneList'); });
        });
    }

    // ── SSE Log Stream ──────────────────────────────────────────────────

    App.connectLogStream = function () {
        if (logEventSource) {
            logEventSource.close();
            logEventSource = null;
        }

        var sseUrl = 'http://localhost:5000/api/log-stream';
        if (App.state.apiToken) sseUrl += '?token=' + encodeURIComponent(App.state.apiToken);
        logEventSource = new EventSource(sseUrl);

        logEventSource.onmessage = (event) => {
            try {
                const log = JSON.parse(event.data);
                if (log.id > App.state.lastLogId) {
                    App.appendLogDOM(log.message, log.type || 'info');
                    App.state.lastLogId = log.id;
                    const liveLog = document.getElementById('liveLog');
                    if (liveLog) liveLog.scrollTop = liveLog.scrollHeight;
                }
            } catch (e) { /* ignore malformed frames */ }
        };

        logEventSource.onerror = () => {
            if (!App.state.serverOnline) {
                logEventSource.close();
                logEventSource = null;
            }
        };
    };

    App.disconnectLogStream = function () {
        if (logEventSource) {
            logEventSource.close();
            logEventSource = null;
        }
    };

    // ── Progress Polling ────────────────────────────────────────────────

    App.startProgressPolling = function () {
        if (pollingInterval) clearInterval(pollingInterval);

        App.connectLogStream();

        pollingInterval = setInterval(async () => {
            if (!App.state.serverOnline) return;

            try {
                const res = await App.apiFetch('/api/progress');
                const data = await res.json();

                if (data.success && data.progress) {
                    const p = data.progress;
                    const isBatchLogin = p.job_type === 'batch_login';
                    const isBulkRelogin = p.job_type === 'bulk_relogin';

                    // Current account label
                    const currentAccount = document.getElementById('currentAccount');
                    if (currentAccount) {
                        if (isBatchLogin && p.status === 'processing') {
                            currentAccount.innerText = p.current_account
                                ? `Logging in: ${p.current_account}`
                                : 'BATCH LOGIN RUNNING...';
                        } else if (isBatchLogin && p.status === 'completed') {
                            currentAccount.innerText = 'BATCH LOGIN COMPLETE';
                        } else if (isBulkRelogin && p.status === 'processing') {
                            currentAccount.innerText = p.current_account
                                ? `Re-logging in: ${p.current_account}`
                                : 'BULK RE-LOGIN RUNNING...';
                        } else if (isBulkRelogin && p.status === 'completed') {
                            currentAccount.innerText = 'BULK RE-LOGIN COMPLETE';
                        } else {
                            currentAccount.innerText = p.current_account
                                ? p.current_account
                                : (App.state.processing ? 'FETCHING_NEXT...' : 'WAITING_FOR_JOB');
                        }
                    }

                    // Step indicator
                    const stepEl = document.getElementById('stepIndicator');
                    if (stepEl && p.step_label) {
                        if (isBatchLogin) stepEl.innerText = '🔑 BATCH LOGIN';
                        else if (isBulkRelogin) stepEl.innerText = '🔄 BULK RE-LOGIN';
                        else stepEl.innerText = p.step_label;
                    } else if (stepEl && !App.state.processing && !isBatchLogin && !isBulkRelogin) {
                        stepEl.innerText = '';
                    }

                    // Progress bar
                    if (p.total > 0) {
                        const pct = Math.floor((p.current / Math.max(1, p.total)) * 100);
                        const bar = document.getElementById('progressBar');
                        const pctEl = document.getElementById('progressPercentage');
                        const txtEl = document.getElementById('progressText');
                        if (bar) bar.style.width = pct + '%';
                        if (pctEl) pctEl.innerText = pct + '%';
                        if (txtEl) txtEl.innerText = `Matrix Progress: ${p.current} / ${p.total}`;
                    }

                    // HUD counters
                    if (p.total   !== undefined) _setEl('totalAccounts', p.total);
                    if (p.success !== undefined) _setEl('totalSuccess', p.success);
                    if (p.failed  !== undefined) _setEl('totalFailed', p.failed);
                    if (p.pending !== undefined) _setEl('totalPending', p.pending);

                    // Labels change based on job type
                    if (isBatchLogin) {
                        _setLabel('totalAccounts', 'Total Accounts', 'fa-users');
                        _setLabel('totalSuccess', 'Logged In', 'fa-check-circle');
                        _setLabel('totalFailed', 'Failed', 'fa-times-circle');
                        _setLabel('totalPending', 'Remaining', 'fa-hourglass-half');
                    } else if (isBulkRelogin) {
                        _setLabel('totalAccounts', 'Total Profiles', 'fa-users');
                        _setLabel('totalSuccess', 'Re-Logged In', 'fa-check-circle');
                        _setLabel('totalFailed', 'Failed', 'fa-times-circle');
                        _setLabel('totalPending', 'Remaining', 'fa-hourglass-half');
                    } else if (p.live_mode) {
                        _setLabel('totalSuccess', 'Live', 'fa-check-circle');
                        _setLabel('totalFailed', 'Missing', 'fa-times-circle');
                    } else {
                        _setLabel('totalSuccess', 'Successful', 'fa-check-circle');
                        _setLabel('totalFailed', 'Failed', 'fa-exclamation-circle');
                        _setLabel('totalPending', 'Pending / Skipped', 'fa-hourglass-half');
                    }

                    // Processing state transitions
                    if (p.status === 'processing' && !App.state.processing) {
                        // Don't lock process buttons for profile manager jobs
                        if (!isBatchLogin && !isBulkRelogin) {
                            App.state.processing = true;
                            App.updateProcessButtons();
                        }
                    } else if (p.status !== 'processing' && App.state.processing) {
                        App.state.processing = false;
                        App.updateProcessButtons();
                        if (p.status === 'completed') {
                            if (isBulkRelogin) {
                                App.log('BULK RE-LOGIN COMPLETE', 'success');
                                const rlMsg = `Re-Login complete — ${p.success || 0} logged in, ${p.failed || 0} failed`;
                                App.toast(rlMsg, 'success');
                                if (p.report_path) _showReloginReportReady(p.report_path, p);
                            } else if (isBatchLogin) {
                                App.log('BATCH LOGIN COMPLETE', 'success');
                            } else {
                                App.log('GHOST SEQUENCE COMPLETE', 'success');
                                App.toast('Processing complete', 'success');
                            }
                        }
                        if (p.status === 'stopped') {
                            App.log('JOB TERMINATED BY USER', 'warning');
                            App.toast('Processing stopped', 'warning');
                        }
                    }
                }
            } catch (e) { /* ignore stealth fails */ }
        }, 1000);
    };

    function _setEl(id, val) {
        const el = document.getElementById(id);
        if (el) el.innerText = val;
    }

    function _setLabel(valueId, label, iconClass) {
        const el = document.getElementById(valueId);
        if (!el) return;
        const card = el.closest('.stat-card');
        if (!card) return;
        const labelEl = card.querySelector('.stat-label');
        if (labelEl) labelEl.innerText = label;
        const iconEl = card.querySelector('.stat-icon i');
        if (iconEl) iconEl.className = 'fas ' + iconClass;
    }

    // ── Process Buttons ─────────────────────────────────────────────────

    App.updateProcessButtons = function () {
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        const selectFileBtn = document.getElementById('selectFileBtn');

        if (!App.state.serverOnline) {
            if (startBtn) startBtn.disabled = true;
            if (stopBtn) stopBtn.disabled = true;
            return;
        }

        if (App.state.processing) {
            if (startBtn) startBtn.disabled = true;
            if (stopBtn) stopBtn.disabled = false;
            if (selectFileBtn) selectFileBtn.disabled = true;
        } else {
            if (startBtn) startBtn.disabled = !App.state.currentFilePath;
            if (stopBtn) stopBtn.disabled = true;
            if (selectFileBtn) selectFileBtn.disabled = false;
        }
    };

    App.setupProcessControls = function () {
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        const resetBtn = document.getElementById('resetBtn');

        if (startBtn) startBtn.addEventListener('click', _startProcessing);
        if (stopBtn) stopBtn.addEventListener('click', _stopProcessing);
        if (resetBtn) resetBtn.addEventListener('click', _resetDashboard);

        _setupRecoveryLists();

        // Random password generator for Processing page
        const processGenPassBtn = document.getElementById('processGenPassBtn');
        if (processGenPassBtn) {
            processGenPassBtn.addEventListener('click', function () {
                var upper = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
                var lower = 'abcdefghjkmnpqrstuvwxyz';
                var digits = '23456789';
                var symbols = '!@#$%&*_+-=?';
                var all = upper + lower + digits + symbols;
                var pwd = '';
                pwd += upper[Math.floor(Math.random() * upper.length)];
                pwd += lower[Math.floor(Math.random() * lower.length)];
                pwd += digits[Math.floor(Math.random() * digits.length)];
                pwd += symbols[Math.floor(Math.random() * symbols.length)];
                for (var i = 4; i < 16; i++) {
                    pwd += all[Math.floor(Math.random() * all.length)];
                }
                pwd = pwd.split('').sort(function () { return Math.random() - 0.5; }).join('');
                document.getElementById('newPassword').value = pwd;
            });
        }
    };

    async function _startProcessing() {
        if (!App.state.currentFilePath) return alert('Need a target payload Excel file.');

        const selectedSteps = App.getSelectedSteps();
        if (selectedSteps.length === 0) return alert('Please select at least one step.');

        const linkCheckbox = document.getElementById('linkCheckbox');
        const linked = linkCheckbox && linkCheckbox.checked && selectedSteps.length >= 2;

        const opsMap = {};
        let allOps = [];
        const stepOpsSelectors = {
            1: '#operationsListStep1 input[type="checkbox"]:checked',
            2: '#operationsList input[type="checkbox"]:checked',
            3: '#operationsListStep3 input[type="checkbox"]:checked',
            4: '#operationsListStep4 input[type="checkbox"]:checked',
        };

        for (const step of selectedSteps) {
            const selector = stepOpsSelectors[step];
            const ops = [];
            document.querySelectorAll(selector).forEach(el => ops.push(el.value));
            if (ops.length === 0) return alert(`Please select at least one operation for Step ${step}.`);
            opsMap[String(step)] = ops.join(',');
            allOps = allOps.concat(ops);
        }

        const payloadParams = {
            file_path: App.state.currentFilePath,
            operations: allOps.join(','),
            new_password: document.getElementById('newPassword')?.value || '',
            recovery_email: _collectRecoveryValues('recovery-email-input'),
            recovery_phone: _collectRecoveryValues('recovery-phone-input'),
            num_workers: parseInt(document.getElementById('numWorkers')?.value) || 5,
            bot_step: selectedSteps[0],
            bot_steps: selectedSteps,
            linked: linked,
            ops_per_step: opsMap,
        };

        try {
            const res = await App.apiFetch('/api/start-processing', {
                method: 'POST',
                body: JSON.stringify(payloadParams)
            });

            const data = await res.json();
            if (data.success) {
                App.state.processing = true;
                App.updateProcessButtons();
                App.log('Ghost Sequence Initiated...', 'info');
            } else {
                alert('Failure: ' + data.message);
            }
        } catch (e) {
            App.log('Network Error initiating ghost sequence: ' + e, 'error');
        }
    }

    async function _stopProcessing() {
        if (!confirm('Stop processing? Active workers will finish their current account before shutting down.')) {
            return;
        }
        try {
            const res = await App.apiFetch('/api/stop-processing', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                App.log('Halt Override Sent. Wrapping up worker threads...', 'warning');
            }
        } catch (e) {
            console.error("Stop ping error", e);
        }
    }

    async function _resetDashboard() {
        if (App.state.processing) return alert('Cannot reset while job is running. Halt first.');

        App.state.currentFilePath = '';
        const filePath = document.getElementById('filePath');
        if (filePath) filePath.value = '';
        _setEl('infoRows', '-');
        _setEl('infoPending', '-');
        _setEl('totalAccounts', '0');
        _setEl('totalSuccess', '0');
        _setEl('totalFailed', '0');
        _setEl('totalPending', '0');

        const progressText = document.getElementById('progressText');
        const progressPct = document.getElementById('progressPercentage');
        const progressBar = document.getElementById('progressBar');
        const currentAccount = document.getElementById('currentAccount');
        if (progressText) progressText.innerText = 'Idle';
        if (progressPct) progressPct.innerText = '0%';
        if (progressBar) progressBar.style.width = '0%';
        if (currentAccount) currentAccount.innerText = 'WAITING_FOR_JOB';

        const liveLog = document.getElementById('liveLog');
        if (liveLog) liveLog.innerHTML = '';
        App.state.lastLogId = 0;

        // Uncheck ALL operation checkboxes
        ['#operationsListStep1', '#operationsList', '#operationsListStep3', '#operationsListStep4']
            .forEach(sel => {
                document.querySelectorAll(`${sel} input[type="checkbox"]`).forEach(cb => cb.checked = false);
            });

        // Clear payload inputs
        var pwdEl = document.getElementById('newPassword');
        if (pwdEl) pwdEl.value = '';

        // Reset recovery lists to single empty input
        ['recoveryEmailList', 'recoveryPhoneList'].forEach(function (listId) {
            var list = document.getElementById(listId);
            if (!list) return;
            var items = list.querySelectorAll('.recovery-item');
            // Keep only first, clear its value
            for (var ri = 1; ri < items.length; ri++) items[ri].remove();
            var firstInput = list.querySelector('input');
            if (firstInput) firstInput.value = '';
            _updateRemoveBtns(listId);
        });

        // Clear backend logs
        try {
            await App.apiFetch('/api/logs/clear', { method: 'POST' });
        } catch (e) { /* ignore if backend not running */ }

        App.log('Full Dashboard Reset completed.', 'info');
        App.updateProcessButtons();
    }

    // ── File Selection ──────────────────────────────────────────────────

    App.setupFileInput = function () {
        const btn = document.getElementById('selectFileBtn');
        if (!btn) return;

        btn.addEventListener('click', async () => {
            if (!window.electronAPI) return alert('Cannot select file: Electron API not available.');

            const filePath = await window.electronAPI.selectFile();
            if (filePath) {
                App.state.currentFilePath = filePath;
                const display = document.getElementById('filePath');
                if (display) display.value = filePath;

                if (App.state.serverOnline) {
                    _fetchFileInfo(filePath);
                }
            }
        });
    };

    async function _fetchFileInfo(filePath) {
        try {
            const response = await App.apiFetch('/api/file-info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_path: filePath })
            });

            const data = await response.json();
            if (data.success) {
                _setEl('infoRows', data.data.total);
                _setEl('infoPending', data.data.pending);
                _setEl('totalAccounts', data.data.total);
                _setEl('totalPending', data.data.pending);
                _setEl('totalSuccess', data.data.success);
                _setEl('totalFailed', data.data.failed);

                App.updateProcessButtons();
                App.log(`Payload Loaded: ${data.data.total} records found.`, 'info');
            } else {
                App.log('Failed to read payload ledger: ' + data.message, 'error');
            }
        } catch (e) {
            App.log('Network Error reading payload: ' + e, 'error');
        }
    }

    // ── Clear Log ───────────────────────────────────────────────────────

    App.setupClearLog = function () {
        const btn = document.getElementById('clearLogBtn');
        if (!btn) return;
        btn.addEventListener('click', async () => {
            if (App.state.serverOnline) {
                try {
                    const res = await App.apiFetch('/api/logs/clear', { method: 'POST' });
                    const data = await res.json();
                    if (data.clear_id) {
                        App.state.lastLogId = data.clear_id;
                    }
                } catch (e) { /* server unreachable */ }
            }

            const liveLog = document.getElementById('liveLog');
            if (liveLog) liveLog.innerHTML = '';
            App.log('Log cleared.', 'info');
        });
    };

    // ── SMS Relay Panel ─────────────────────────────────────────────────

    App.setupSmsRelayPanel = function () {
        const testBtn = document.getElementById('smsTestBtn');
        const checkBtn = document.getElementById('smsCheckBtn');
        const lastCode = document.getElementById('smsLastCode');
        const lastSender = document.getElementById('smsLastSender');
        const relayStatus = document.getElementById('smsRelayStatus');
        const testResult = document.getElementById('smsTestResult');

        if (!testBtn) return;

        testBtn.addEventListener('click', async () => {
            testResult.innerText = 'Sending...';
            try {
                const res = await App.apiFetch('/api/sms-code', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        code: String(Math.floor(100000 + Math.random() * 900000)),
                        sender: '+880TEST',
                        full_message: 'G-TEST manual test from Electron UI',
                        timestamp: Date.now() / 1000
                    })
                });
                const data = await res.json();
                if (data.success) {
                    testResult.innerText = 'Test code sent! Check live log.';
                    testResult.style.color = '#2ecc71';
                } else {
                    testResult.innerText = 'Failed: ' + (data.error || 'unknown');
                    testResult.style.color = '#e74c3c';
                }
            } catch (e) {
                testResult.innerText = 'Backend offline';
                testResult.style.color = '#e74c3c';
            }
            setTimeout(() => { testResult.innerText = ''; }, 5000);
        });

        checkBtn.addEventListener('click', async () => {
            try {
                const res = await App.apiFetch('/api/sms-code?max_age=9999&peek=1');
                const data = await res.json();
                if (data.success && data.code) {
                    lastCode.innerText = data.code;
                    lastSender.innerText = data.sender || 'unknown';
                    relayStatus.innerText = 'Code available';
                    relayStatus.style.color = '#2ecc71';
                } else {
                    lastCode.innerText = '--';
                    relayStatus.innerText = 'No unused codes';
                    relayStatus.style.color = '#f39c12';
                }
            } catch (e) {
                relayStatus.innerText = 'Backend offline';
                relayStatus.style.color = '#e74c3c';
            }
        });

        // Auto-poll every 5s when dashboard is visible
        setInterval(async () => {
            const dashboard = document.getElementById('dashboard');
            if (!dashboard || !dashboard.classList.contains('active')) return;
            if (!App.state.serverOnline) return;
            try {
                const res = await App.apiFetch('/api/sms-code?max_age=300&peek=1');
                const data = await res.json();
                if (data.success && data.code) {
                    lastCode.innerText = data.code;
                    lastSender.innerText = data.sender || '';
                    relayStatus.innerText = 'Code available';
                    relayStatus.style.color = '#2ecc71';
                }
            } catch (e) { /* silent */ }
        }, 5000);
    };

})(window.App || (window.App = {}));
