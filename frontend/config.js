(function () {
    const origin = 'http://localhost:9090';

    window.CV_MATCH_CONFIG = Object.assign({
        apiBaseUrl: `${origin.replace(/\/$/, '')}/api`
    }, window.CV_MATCH_CONFIG || {});
})();
