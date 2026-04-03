/**
 * auth.js — Centralized API fetch wrapper. Licensing removed.
 */
(function (App) {
    'use strict';

    App.state = App.state || {};
    App.state.apiToken = 'local';
    App.state.authenticated = false;

    const API_BASE = 'http://localhost:5000';

    // ── Centralized API fetch ────────────────────────────────────────────────

    App.apiFetch = function (url, options) {
        options = options || {};
        if (url.startsWith('/')) url = API_BASE + url;
        options.headers = options.headers || {};
        if (!options.headers['Content-Type'] && options.method !== 'GET') {
            options.headers['Content-Type'] = 'application/json';
        }
        return fetch(url, options);
    };

    // ── Auto-unlock once backend is ready ────────────────────────────────────

    function unlockApp() {
        App.state.authenticated = true;
        var overlay = document.getElementById('loginOverlay');
        if (overlay) overlay.style.display = 'none';
        if (typeof App.onAuthenticated === 'function') {
            App.onAuthenticated();
        }
    }

    // ── Splash screen helpers ────────────────────────────────────────────────

    function _setSplashStatus(msg) {
        var el = document.getElementById('splashStatus');
        if (el) el.textContent = msg;
    }

    function _hideSplash() {
        var splash = document.getElementById('launchSplash');
        if (!splash) return;
        splash.style.opacity = '0';
        setTimeout(function () {
            if (splash.parentNode) splash.parentNode.removeChild(splash);
        }, 520);
    }

    // ── Backend ready ────────────────────────────────────────────────────────

    function unlockApp() {
        App.state.authenticated = true;
        var overlay = document.getElementById('loginOverlay');
        if (overlay) overlay.style.display = 'none';
        _setSplashStatus('Ready!');
        setTimeout(_hideSplash, 300);
        if (typeof App.onAuthenticated === 'function') {
            App.onAuthenticated();
        }
    }

    var _attempt = 0;
    function waitForBackend() {
        _attempt++;
        // Update splash status every few attempts so the user sees progress
        if (_attempt <= 3)       _setSplashStatus('Starting backend…');
        else if (_attempt <= 8)  _setSplashStatus('Loading modules…');
        else if (_attempt <= 15) _setSplashStatus('Almost ready…');
        else                     _setSplashStatus('Still loading… (first run may take longer)');

        fetch(API_BASE + '/api/health')
            .then(function (r) { if (r.ok) unlockApp(); else setTimeout(waitForBackend, 1000); })
            .catch(function () { setTimeout(waitForBackend, 1000); });
    }

    // Also listen for the IPC backend-ready event from main.js as a fast path
    if (window.electronAPI && typeof window.electronAPI.onBackendReady === 'function') {
        window.electronAPI.onBackendReady(function () {
            unlockApp();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { setTimeout(waitForBackend, 200); });
    } else {
        setTimeout(waitForBackend, 200);
    }

})(window.App || (window.App = {}));
