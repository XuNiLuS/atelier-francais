/* Mesure facultative : aucun appel à Google avant un accord explicite. */
(() => {
  'use strict';

  const noop = () => {};
  window.atelierAnalytics = { quizStarted: noop, quizCompleted: noop, resetAttempt: noop };
  const banner = document.getElementById('analytics-consent');
  const acceptButton = document.getElementById('analytics-accept');
  const rejectButton = document.getElementById('analytics-reject');
  const settingsButton = document.getElementById('analytics-settings');
  const status = document.getElementById('analytics-status');
  if (!banner || !acceptButton || !rejectButton || !settingsButton || !status) return;

  let config = {};
  try {
    config = JSON.parse(document.getElementById('analytics-config')?.textContent || '{}') || {};
  } catch (_) { /* Une configuration invalide laisse la mesure désactivée. */ }

  const retention = 180 * 24 * 60 * 60 * 1000;
  const basePath = typeof config.base_path === 'string' ? config.base_path.replace(/\/+$/, '') : '';
  const validPath = /^\/[a-zA-Z0-9_-]+(?:\/[a-zA-Z0-9_-]+)*$/.test(basePath);
  const production = validPath
    && config.production_origin === 'https://xunilus.github.io'
    && window.location.origin === config.production_origin
    && (window.location.pathname === basePath || window.location.pathname.startsWith(`${basePath}/`));
  const measurementId = typeof config.measurement_id === 'string'
    && /^G-[A-Z0-9]{6,20}$/.test(config.measurement_id) ? config.measurement_id : '';
  const storageKey = `atelier.analytics-consent.v1:${basePath || '/'}`;
  const cookiePath = `${basePath}/`;
  const disabledKey = measurementId ? `ga-disable-${measurementId}` : '';
  let choice = null;
  let savedAt = 0;
  let storageAvailable = true;
  let expiryTimer;
  let tagStarted = false;
  let stopping = false;
  let suspended = false;
  let loadFailed = false;
  let tag;
  let started = false;
  let completed = false;
  if (disabledKey) window[disabledKey] = true;

  function readChoice() {
    try {
      const stored = JSON.parse(window.localStorage.getItem(storageKey));
      if (stored?.version === 1 && ['accepted', 'rejected'].includes(stored.choice)
        && Number.isFinite(stored.saved_at) && stored.saved_at > 0
        && stored.saved_at <= Date.now() && Date.now() - stored.saved_at < retention) return stored;
    } catch (_) { /* Stockage bloqué ou ancien choix illisible : aucun accord. */ }
    return null;
  }

  function persistChoice(nextChoice) {
    savedAt = Date.now();
    try {
      window.localStorage.setItem(storageKey, JSON.stringify({ version: 1, choice: nextChoice, saved_at: savedAt }));
      storageAvailable = true;
    } catch (_) {
      storageAvailable = false;
      // Si le quota empêche l'écriture, ne pas conserver un ancien accord au retrait.
      try { window.localStorage.removeItem(storageKey); } catch (_) { /* Stockage bloqué. */ }
    }
  }

  function clearProjectCookies() {
    if (!production) return;
    const names = new Set(['atelier_ga']);
    if (measurementId) names.add(`atelier_ga_${measurementId.slice(2)}`);
    try {
      for (const entry of document.cookie.split(';')) {
        const name = entry.trim().split('=')[0];
        if (/^atelier_ga(?:_[A-Za-z0-9_]+)?$/.test(name)) names.add(name);
      }
      for (const name of names) {
        // Même chemin et même hôte que la configuration GA ; aucun cookie d'une autre app.
        document.cookie = `${name}=; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=${cookiePath}; SameSite=Lax; Secure`;
      }
    } catch (_) { /* Le navigateur peut bloquer totalement les cookies. */ }
  }

  function updateStatus() {
    let text = choice === 'accepted'
      ? 'Mesure d’audience autorisée. Tu peux la refuser à tout moment.'
      : choice === 'rejected'
        ? 'Mesure d’audience refusée. Aucun appel à Google Analytics.'
        : 'Sans ton accord, aucun appel à Google Analytics.';
    if (!production) text += ' Prévisualisation : aucune mesure n’est envoyée depuis cette adresse.';
    else if (!measurementId) text += ' La mesure d’audience n’est pas configurée sur cette page.';
    else if (loadFailed) text += ' Le chargement de la mesure a échoué ; le quiz reste utilisable.';
    if (!storageAvailable) text += ' Le stockage est indisponible : ce choix vaut uniquement pour cette page.';
    if (choice === 'accepted' && tagStarted) {
      text += ' Si tu refuses maintenant, la page sera rechargée et le quiz en cours recommencera.';
    }
    status.textContent = text;
    acceptButton.setAttribute('aria-pressed', String(choice === 'accepted'));
    rejectButton.setAttribute('aria-pressed', String(choice === 'rejected'));
  }

  function showBanner(open, focus = false) {
    const restoreFocus = !open && banner.contains(document.activeElement);
    banner.hidden = !open;
    settingsButton.setAttribute('aria-expanded', String(open));
    updateStatus();
    if (open && focus) banner.focus();
    else if (restoreFocus) settingsButton.focus({ preventScroll: true });
  }

  function stopMeasurement() {
    if (disabledKey) window[disabledKey] = true;
    clearProjectCookies();
    if (!tagStarted || stopping) return;
    stopping = true;
    if (Array.isArray(window.dataLayer)) window.dataLayer.length = 0;
    tag?.remove();
    // Retirer la balise ne désinstalle pas ses écouteurs : recharger après avoir enregistré le refus.
    window.location.reload();
  }

  function checkExpiry() {
    if (choice && Date.now() - savedAt >= retention) {
      choice = null;
      stopMeasurement();
      showBanner(true);
    }
    return choice === 'accepted';
  }

  function scheduleExpiry() {
    window.clearTimeout(expiryTimer);
    if (!choice) return;
    const remaining = Math.max(0, savedAt + retention - Date.now());
    expiryTimer = window.setTimeout(() => {
      checkExpiry();
      scheduleExpiry();
    }, Math.min(remaining, 2147483647));
  }

  function canMeasure() {
    return checkExpiry() && production && measurementId && !stopping && !suspended && !loadFailed;
  }

  function gtag() {
    if (canMeasure()) window.dataLayer.push(arguments);
  }

  function pageMetadata() {
    // Ces valeurs viennent du catalogue généré, jamais des réponses ni du DOM.
    const metadata = {};
    if (['4e', '3e', 'seconde'].includes(config.level)) metadata.education_level = config.level;
    if (metadata.education_level && typeof config.quiz_id === 'string'
      && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(config.quiz_id) && config.quiz_id.length <= 100
      && typeof config.quiz_theme === 'string' && config.quiz_theme.trim() && config.quiz_theme.length <= 100) {
      metadata.quiz_id = config.quiz_id;
      metadata.quiz_theme = config.quiz_theme;
    }
    return metadata;
  }

  function startMeasurement() {
    if (!canMeasure() || tagStarted) return;
    tagStarted = true;
    window[disabledKey] = false;
    window.dataLayer = [];
    window.gtag = gtag;
    const pageLocation = window.location.origin + window.location.pathname;
    const metadata = pageMetadata();
    const pageTitle = metadata.quiz_theme
      ? `${metadata.quiz_theme} · ${metadata.education_level} · L’atelier de Madame Daadoun`
      : metadata.education_level
        ? `Quiz de ${metadata.education_level} · L’atelier de Madame Daadoun`
        : 'L’atelier de Madame Daadoun';
    gtag('consent', 'default', {
      analytics_storage: 'denied', ad_storage: 'denied',
      ad_user_data: 'denied', ad_personalization: 'denied',
    });
    gtag('consent', 'update', { analytics_storage: 'granted' });
    gtag('js', new Date());
    gtag('config', measurementId, {
      send_page_view: false,
      page_location: pageLocation,
      page_referrer: '',
      page_title: pageTitle,
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
      cookie_prefix: 'atelier',
      cookie_domain: 'none',
      cookie_path: cookiePath,
      cookie_expires: retention / 1000,
      cookie_update: false,
      cookie_flags: 'SameSite=Lax;Secure',
    });
    gtag('event', 'page_view', { ...metadata, page_location: pageLocation, page_referrer: '' });
    try {
      tag = document.createElement('script');
      tag.async = true;
      tag.referrerPolicy = 'no-referrer';
      tag.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`;
      tag.onerror = () => {
        loadFailed = true;
        window[disabledKey] = true;
        window.dataLayer.length = 0;
        updateStatus();
      };
      document.head.appendChild(tag);
    } catch (_) {
      loadFailed = true;
      window[disabledKey] = true;
      window.dataLayer.length = 0;
      updateStatus();
    }
  }

  function recordQuizEvent(name) {
    // Seuls des libellés du catalogue sont admis ; aucun argument du parcours n'est lu.
    const metadata = pageMetadata();
    if (canMeasure() && tagStarted && metadata.quiz_id) gtag('event', name, metadata);
  }

  window.atelierAnalytics = {
    quizStarted() {
      if (started) return;
      started = true;
      recordQuizEvent('quiz_start');
    },
    quizCompleted() {
      if (completed) return;
      completed = true;
      recordQuizEvent('quiz_complete');
    },
    resetAttempt() { started = false; completed = false; },
  };

  acceptButton.addEventListener('click', () => {
    choice = 'accepted';
    persistChoice(choice);
    scheduleExpiry();
    startMeasurement();
    showBanner(false);
  });
  rejectButton.addEventListener('click', () => {
    choice = 'rejected';
    persistChoice(choice);
    scheduleExpiry();
    stopMeasurement();
    showBanner(false);
  });
  settingsButton.setAttribute('aria-controls', 'analytics-consent');
  settingsButton.hidden = false;
  banner.setAttribute('tabindex', '-1');
  settingsButton.addEventListener('click', () => {
    checkExpiry();
    showBanner(true, true);
  });
  function refreshStoredChoice() {
    const previousChoice = choice;
    const stored = readChoice();
    choice = stored?.choice || null;
    savedAt = stored?.saved_at || 0;
    suspended = false;
    if (choice === 'accepted') {
      startMeasurement();
      if (canMeasure() && tagStarted) window[disabledKey] = false;
    } else stopMeasurement();
    scheduleExpiry();
    showBanner(!choice || (choice === previousChoice && !banner.hidden));
  }

  // Un retrait effectué dans un autre onglet arrête aussi cette page.
  window.addEventListener('storage', (event) => {
    if (event.key === storageKey || event.key === null) refreshStoredChoice();
  });
  // Le cache précédent/suivant conserve le JavaScript : suspendre avant de le quitter,
  // puis relire le choix avant de laisser une ancienne balise reprendre ses envois.
  window.addEventListener('pagehide', () => {
    suspended = true;
    if (disabledKey) window[disabledKey] = true;
  });
  window.addEventListener('pageshow', (event) => {
    if (event.persisted) refreshStoredChoice();
  });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible') return;
    if (storageAvailable) refreshStoredChoice();
    else checkExpiry(); // Un choix non mémorisable reste limité à cette page active.
  });

  const stored = readChoice();
  choice = stored?.choice || null;
  savedAt = stored?.saved_at || 0;
  if (choice === 'accepted') startMeasurement();
  else clearProjectCookies();
  scheduleExpiry();
  showBanner(!choice);
})();
