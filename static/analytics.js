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
  const acceptLabel = acceptButton.textContent || 'Accepter';

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
  let loadingTimer;
  let tagStarted = false;
  let stopping = false;
  let suspended = false;
  let tagState = 'idle';
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
        ? 'Statistiques refusées : aucun appel à Google Analytics.'
        : 'Facultatif. Ton choix reste modifiable en bas de page.';
    const canRetry = choice === 'accepted' && ['failed', 'slow'].includes(tagState);
    if (choice === 'accepted' && production && measurementId) {
      if (tagState === 'loading') text = 'Choix enregistré. Chargement de la balise en cours…';
      else if (tagState === 'loaded') text = 'Balise chargée. Les rapports peuvent mettre quelques minutes à s’actualiser.';
      else if (tagState === 'slow') text = 'Choix enregistré. Le chargement prend du temps ; il n’est pas encore confirmé.';
      else if (tagState === 'failed') text = 'Le chargement de la balise a échoué ou a été bloqué. Le quiz reste utilisable.';
    }
    if (!production) text += ' Prévisualisation : aucune mesure n’est envoyée depuis cette adresse.';
    else if (!measurementId) text += ' La mesure d’audience n’est pas configurée sur cette page.';
    if (!storageAvailable) text += ' Le stockage est indisponible : ce choix vaut uniquement pour cette page.';
    if (choice === 'accepted' && tagStarted) {
      text += canRetry
        ? ' Réessayer ou refuser recharge la page et recommence le quiz.'
        : ' Refuser recharge la page et recommence le quiz.';
    }
    status.textContent = text;
    acceptButton.textContent = canRetry ? 'Réessayer' : acceptLabel;
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
    window.clearTimeout(loadingTimer);
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
    return checkExpiry() && production && measurementId && !stopping && !suspended && tagState !== 'failed';
  }

  function gtag() {
    if (!canMeasure()) return;
    try { window.dataLayer.push(arguments); } catch (_) { failLoading(); }
  }

  function failLoading() {
    if (stopping) return;
    tagState = 'failed';
    window.clearTimeout(loadingTimer);
    if (disabledKey) window[disabledKey] = true;
    if (Array.isArray(window.dataLayer)) window.dataLayer.length = 0;
    updateStatus();
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
    tagState = 'loading';
    try {
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
      if (tagState === 'failed') return;
      tag = document.createElement('script');
      tag.async = true;
      tag.referrerPolicy = 'no-referrer';
      tag.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`;
      tag.onload = () => {
        if (stopping || tagState === 'failed') return;
        window.clearTimeout(loadingTimer);
        tagState = 'loaded';
        updateStatus();
      };
      tag.onerror = failLoading;
      loadingTimer = window.setTimeout(() => {
        if (stopping || tagState !== 'loading') return;
        tagState = 'slow'; // Un délai dépassé n'est pas une preuve d'échec réseau.
        updateStatus();
      }, 20000);
      document.head.appendChild(tag);
    } catch (_) { failLoading(); }
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
    if (choice === 'accepted' && ['failed', 'slow'].includes(tagState)) {
      // Réessai explicite seulement : la page repart proprement, avec le choix déjà enregistré.
      stopping = true;
      suspended = true;
      if (disabledKey) window[disabledKey] = true;
      window.clearTimeout(loadingTimer);
      tag?.remove();
      if (Array.isArray(window.dataLayer)) window.dataLayer.length = 0;
      window.location.reload();
      return;
    }
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
  // Laisser GA terminer les envois déjà autorisés au départ ; seuls nos nouveaux hooks
  // sont suspendus. Au retour du cache, vérifier le choix avant les écouteurs de la balise.
  window.addEventListener('pagehide', () => {
    suspended = true;
  });
  window.addEventListener('pageshow', (event) => {
    if (event.persisted) refreshStoredChoice();
  }, { capture: true });
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
