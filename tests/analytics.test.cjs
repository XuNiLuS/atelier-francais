/* Exécuter avec node --test tests/analytics.test.cjs ; aucune dépendance ni requête réseau. */
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'static', 'analytics.js'), 'utf8');
const ORIGIN = 'https://xunilus.github.io';
const BASE = '/atelier-francais';
const KEY = `atelier.analytics-consent.v1:${BASE}`;
const ID = 'G-TEST123456';
const NOW = Date.UTC(2026, 8, 30, 12);
const RETENTION = 180 * 24 * 60 * 60 * 1000;

function environment(options = {}) {
  let now = NOW;
  let reloads = 0;
  let nextTimer = 0;
  const scripts = [];
  const cookieWrites = [];
  const timers = new Map();
  const events = new Map();
  const eventOptions = new Map();
  const documentEvents = new Map();
  const stored = new Map(Object.entries(options.storage || {}));
  const config = {
    measurement_id: ID, production_origin: ORIGIN, base_path: BASE,
    level: '4e', quiz_id: '4e-temps-recit', quiz_theme: 'Les temps du récit',
    ...options.config,
  };
  const nodes = new Map();
  const document = {
    activeElement: null,
    title: 'titre-personnel@example.org',
    referrer: 'https://ecole.example.org/eleve/prenom?email=prive@example.org',
    visibilityState: 'visible',
    addEventListener(name, handler) { documentEvents.set(name, handler); },
    getElementById(id) { return nodes.get(id) || null; },
    createElement(tag) { return makeNode(tag); },
    head: { appendChild(node) {
      if (options.appendBlocked) throw new Error('Insertion de balise bloquée');
      scripts.push(node);
      return node;
    } },
  };
  Object.defineProperty(document, 'cookie', {
    get() { return options.cookies || ''; },
    set(value) { cookieWrites.push(value); },
  });
  function makeNode(id) {
    const listeners = new Map();
    return {
      id, hidden: ['analytics-consent', 'analytics-settings'].includes(id), textContent: '', attributes: {}, removed: false,
      addEventListener(name, handler) { listeners.set(name, handler); },
      setAttribute(name, value) { this.attributes[name] = value; },
      focus() { document.activeElement = this; },
      contains(node) {
        return node === this || (id === 'analytics-consent' && ['analytics-accept', 'analytics-reject', 'analytics-status'].includes(node?.id));
      },
      click() { this.focus(); listeners.get('click')?.(); },
      remove() { this.removed = true; },
    };
  }
  for (const id of ['analytics-config', 'analytics-consent', 'analytics-accept', 'analytics-reject', 'analytics-settings', 'analytics-status']) {
    nodes.set(id, makeNode(id));
  }
  nodes.get('analytics-config').textContent = options.rawConfig ?? JSON.stringify(config);
  nodes.get('analytics-accept').textContent = 'Accepter';
  if (options.missingNode) nodes.delete(options.missingNode);
  const url = new URL(options.url || `${ORIGIN}${BASE}/quiz/4e-temps-recit/?email=prive@example.org#prenom`);
  const window = {
    location: {
      origin: url.origin, pathname: url.pathname, href: url.href, search: url.search, hash: url.hash,
      reload() { reloads += 1; },
    },
    localStorage: {
      getItem(key) {
        if (options.storageBlocked) throw new Error('Stockage inaccessible');
        return stored.get(key) ?? null;
      },
      setItem(key, value) {
        if (options.storageBlocked || options.storageFull) throw new Error('Stockage inaccessible');
        stored.set(key, value);
      },
      removeItem(key) {
        if (options.storageBlocked) throw new Error('Stockage inaccessible');
        stored.delete(key);
      },
    },
    setTimeout(callback, delay) { const id = ++nextTimer; timers.set(id, { callback, delay }); return id; },
    clearTimeout(id) { timers.delete(id); },
    addEventListener(name, handler, settings) { events.set(name, handler); eventOptions.set(name, settings); },
  };
  class Clock extends Date {
    constructor(...args) { super(...(args.length ? args : [now])); }
    static now() { return now; }
  }
  vm.runInNewContext(source, { window, document, Date: Clock });
  return {
    window, document, nodes, scripts, stored, cookieWrites, timers, eventOptions,
    get reloads() { return reloads; },
    commands() { return JSON.parse(JSON.stringify((window.dataLayer || []).map((item) => Array.from(item)))); },
    clicks(id) { nodes.get(id).click(); },
    dispatchWindow(name, event = {}) { events.get(name)?.(event); },
    runTimer(delay) {
      const entry = [...timers].find(([, timer]) => timer.delay === delay);
      if (!entry) return false;
      now += delay;
      timers.delete(entry[0]);
      entry[1].callback();
      return true;
    },
    visibility(state) {
      document.visibilityState = state;
      documentEvents.get('visibilitychange')?.();
    },
    changeStorage(key, value) {
      if (key === null) stored.clear();
      else if (value === null) stored.delete(key);
      else stored.set(key, value);
      events.get('storage')?.({ key });
    },
    expire() {
      now += RETENTION;
      const callbacks = [...timers.values()];
      timers.clear();
      for (const { callback } of callbacks) callback();
    },
  };
}

function choice(value, savedAt = NOW - 1000) {
  return JSON.stringify({ version: 1, choice: value, saved_at: savedAt });
}

function events(env, name) {
  return env.commands().filter((item) => item[0] === 'event' && (!name || item[1] === name));
}

test('Sans choix, aucun Google, cookie de mesure créé ou événement mis en attente', () => {
  const env = environment();
  assert.equal(env.scripts.length, 0);
  assert.equal(env.window.dataLayer, undefined);
  assert.equal(env.nodes.get('analytics-consent').hidden, false);
  assert.equal(env.nodes.get('analytics-settings').hidden, false);
  assert.equal(env.window[`ga-disable-${ID}`], true);
  env.window.atelierAnalytics.quizStarted();
  env.window.atelierAnalytics.quizCompleted();
  assert.equal(env.window.dataLayer, undefined);
  assert.equal(env.stored.size, 0);
  assert.ok(env.cookieWrites.every((item) => item.includes('Max-Age=0')));
});

test('Refuser mémorise le choix, sans script, ping ni commande de consentement Google', () => {
  const env = environment();
  env.clicks('analytics-reject');
  assert.deepEqual(JSON.parse(env.stored.get(KEY)), { version: 1, choice: 'rejected', saved_at: NOW });
  assert.equal(env.scripts.length, 0);
  assert.equal(env.window.dataLayer, undefined);
  assert.equal(env.reloads, 0);
  assert.equal(env.nodes.get('analytics-consent').hidden, true);
  assert.equal(env.document.activeElement, env.nodes.get('analytics-settings'));
  assert.doesNotMatch(env.nodes.get('analytics-status').textContent, /recharge la page/);
  assert.match(env.nodes.get('analytics-status').textContent, /refusée/);
  env.clicks('analytics-settings');
  assert.equal(env.nodes.get('analytics-consent').hidden, false);
  assert.equal(env.nodes.get('analytics-settings').attributes['aria-expanded'], 'true');
  assert.equal(env.nodes.get('analytics-accept').attributes['aria-pressed'], 'false');
  assert.equal(env.nodes.get('analytics-reject').attributes['aria-pressed'], 'true');
  assert.equal(env.document.activeElement, env.nodes.get('analytics-consent'));
});

test('Accepter configure une mesure limitée et une seule page_view nettoyée', () => {
  const env = environment();
  env.clicks('analytics-accept');
  env.clicks('analytics-accept');
  assert.equal(env.scripts.length, 1);
  assert.equal(env.scripts[0].src, `https://www.googletagmanager.com/gtag/js?id=${ID}`);
  assert.equal(env.scripts[0].referrerPolicy, 'no-referrer');
  assert.equal(env.window[`ga-disable-${ID}`], false);
  const commands = env.commands();
  assert.deepEqual(commands[0], ['consent', 'default', {
    analytics_storage: 'denied', ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied',
  }]);
  assert.deepEqual(commands[1], ['consent', 'update', { analytics_storage: 'granted' }]);
  const setup = commands.find((item) => item[0] === 'config')[2];
  assert.equal(setup.send_page_view, false);
  assert.equal(setup.page_location, `${ORIGIN}${BASE}/quiz/4e-temps-recit/`);
  assert.equal(setup.page_referrer, '');
  assert.equal(setup.page_title, 'Les temps du récit · 4e · L’atelier de Madame Daadoun');
  assert.equal(setup.allow_google_signals, false);
  assert.equal(setup.allow_ad_personalization_signals, false);
  assert.equal(setup.cookie_prefix, 'atelier');
  assert.equal(setup.cookie_path, `${BASE}/`);
  assert.equal(setup.cookie_domain, 'none');
  assert.equal(setup.cookie_update, false);
  assert.equal(setup.cookie_expires, RETENTION / 1000);
  assert.equal(setup.cookie_flags, 'SameSite=Lax;Secure');
  assert.equal(events(env, 'page_view').length, 1);
  assert.deepEqual(events(env, 'page_view')[0][2], {
    education_level: '4e', quiz_id: '4e-temps-recit', quiz_theme: 'Les temps du récit',
    page_location: `${ORIGIN}${BASE}/quiz/4e-temps-recit/`, page_referrer: '',
  });
  assert.equal(env.document.activeElement, env.nodes.get('analytics-settings'));
  env.clicks('analytics-settings');
  assert.match(env.nodes.get('analytics-status').textContent, /Refuser recharge la page et recommence le quiz/);
  assert.doesNotMatch(JSON.stringify(commands), /prive@|prenom|ecole\.example|titre-personnel/);
});

test('Les événements quiz ne contiennent que le catalogue et sont uniques par essai', () => {
  const env = environment();
  env.clicks('analytics-accept');
  for (let index = 0; index < 3; index += 1) {
    env.window.atelierAnalytics.quizStarted({ email: 'eleve@example.org', response: 'a' });
    env.window.atelierAnalytics.quizCompleted({ score: 20, answers: ['a', 'b'] });
  }
  assert.equal(events(env, 'quiz_start').length, 1);
  assert.equal(events(env, 'quiz_complete').length, 1);
  for (const event of [...events(env, 'quiz_start'), ...events(env, 'quiz_complete')]) {
    assert.deepEqual(event[2], {
      education_level: '4e', quiz_id: '4e-temps-recit', quiz_theme: 'Les temps du récit',
    });
  }
  assert.doesNotMatch(JSON.stringify(env.commands()), /eleve@|score|answers|response/);
  env.window.atelierAnalytics.resetAttempt();
  env.window.atelierAnalytics.quizStarted();
  env.window.atelierAnalytics.quizCompleted();
  assert.equal(events(env, 'quiz_start').length, 2);
  assert.equal(events(env, 'quiz_complete').length, 2);
});

test('Un accord tardif ne rattrape aucun événement survenu sans consentement', () => {
  const env = environment();
  env.clicks('analytics-reject');
  env.window.atelierAnalytics.quizStarted();
  env.window.atelierAnalytics.quizCompleted();
  env.clicks('analytics-accept');
  env.window.atelierAnalytics.quizStarted();
  env.window.atelierAnalytics.quizCompleted();
  assert.equal(events(env, 'quiz_start').length, 0);
  assert.equal(events(env, 'quiz_complete').length, 0);
  env.window.atelierAnalytics.resetAttempt();
  env.window.atelierAnalytics.quizStarted();
  assert.equal(events(env, 'quiz_start').length, 1);
});

test('Le retrait désactive GA avant rechargement et cible uniquement les cookies du projet', () => {
  const env = environment({ cookies: 'atelier_ga=1; atelier_ga_TEST123456=2; _ga=autre; atelier_preferences=non; autre_ga=non' });
  env.clicks('analytics-accept');
  env.window.atelierAnalytics.quizStarted();
  env.clicks('analytics-reject');
  assert.equal(env.window[`ga-disable-${ID}`], true);
  assert.equal(env.reloads, 1);
  assert.equal(env.scripts[0].removed, true);
  assert.equal(JSON.parse(env.stored.get(KEY)).choice, 'rejected');
  assert.deepEqual(env.commands(), []);
  assert.ok(env.cookieWrites.length > 0);
  for (const deletion of env.cookieWrites) {
    assert.match(deletion, /^atelier_ga(?:_[A-Z0-9]+)?=;/);
    assert.ok(deletion.includes(`Path=${BASE}/;`));
    assert.doesNotMatch(deletion, /Domain=|Path=\/;|atelier_preferences|autre_ga/);
  }
  env.window.atelierAnalytics.quizCompleted();
  assert.deepEqual(env.commands(), []);
});

test('La prévisualisation et les projets voisins ne mesurent rien, même après accord', () => {
  for (const url of [
    'http://127.0.0.1:8000/',
    `http://localhost:8000${BASE}/`,
    `http://xunilus.github.io${BASE}/`,
    `https://autre.github.io${BASE}/`,
    `${ORIGIN}/autre-projet/`,
    `${ORIGIN}${BASE}-voisin/`,
    `${ORIGIN}/`,
  ]) {
    const env = environment({ url });
    env.clicks('analytics-accept');
    env.window.atelierAnalytics.quizStarted();
    env.window.atelierAnalytics.quizCompleted();
    assert.equal(env.scripts.length, 0, url);
    assert.equal(env.window.dataLayer, undefined, url);
    assert.equal(env.cookieWrites.length, 0, url);
    assert.match(env.nodes.get('analytics-status').textContent, /Prévisualisation/);
  }
});

test('Un choix valide est restauré sans prolonger sa durée', () => {
  for (const savedChoice of ['accepted', 'rejected']) {
    const value = choice(savedChoice);
    const env = environment({ storage: { [KEY]: value } });
    assert.equal(env.scripts.length, savedChoice === 'accepted' ? 1 : 0);
    assert.equal(env.nodes.get('analytics-consent').hidden, true);
    assert.equal(env.stored.get(KEY), value);
  }
});

test('Les choix expirés, futurs ou invalides ne valent jamais accord', () => {
  for (const value of [choice('accepted', NOW - RETENTION), choice('accepted', NOW + 1000), '{}', 'null', 'malformé']) {
    const env = environment({ storage: { [KEY]: value } });
    assert.equal(env.scripts.length, 0);
    assert.equal(env.nodes.get('analytics-consent').hidden, false);
  }
  const env = environment({ storage: { [KEY]: choice('accepted') } });
  env.expire();
  assert.equal(env.window[`ga-disable-${ID}`], true);
  assert.equal(env.reloads, 1);
  assert.equal(env.nodes.get('analytics-consent').hidden, false);
});

test('Le stockage bloqué laisse le choix explicite utilisable uniquement sur la page', () => {
  const env = environment({ storageBlocked: true });
  env.clicks('analytics-accept');
  assert.equal(env.scripts.length, 1);
  assert.match(env.nodes.get('analytics-status').textContent, /uniquement pour cette page/);
  env.clicks('analytics-reject');
  assert.equal(env.window[`ga-disable-${ID}`], true);
  assert.equal(env.reloads, 1);
  const full = environment({ storageFull: true, storage: { [KEY]: choice('accepted') } });
  full.clicks('analytics-reject');
  assert.equal(full.stored.has(KEY), false);
});

test('Le retrait dans un autre onglet arrête aussi les événements de la page ouverte', () => {
  const env = environment({ storage: { [KEY]: choice('accepted') } });
  env.changeStorage('autre-projet', 'non');
  assert.equal(env.reloads, 0);
  env.changeStorage(KEY, choice('rejected', NOW));
  assert.equal(env.reloads, 1);
  assert.equal(env.window[`ga-disable-${ID}`], true);
  env.window.atelierAnalytics.quizStarted();
  assert.equal(events(env).length, 0);
});

test('Une mesure bloquée ou une configuration absente ne casse jamais le quiz', () => {
  const env = environment();
  env.clicks('analytics-accept');
  env.scripts[0].onerror();
  env.window.atelierAnalytics.quizStarted();
  assert.equal(events(env).length, 0);
  assert.match(env.nodes.get('analytics-status').textContent, /quiz reste utilisable/);
  for (const options of [
    { rawConfig: 'JSON invalide' },
    { config: { measurement_id: '' } },
    { config: { measurement_id: 'G-ID&autre=oui' } },
    { missingNode: 'analytics-consent' },
  ]) {
    const invalid = environment(options);
    invalid.window.atelierAnalytics.quizStarted();
    invalid.window.atelierAnalytics.quizCompleted();
    invalid.clicks('analytics-accept');
    assert.equal(invalid.scripts.length, 0);
  }
});

test('Un retour précédent/suivant respecte un retrait intervenu pendant la mise en cache', () => {
  const env = environment({ storage: { [KEY]: choice('accepted') } });
  env.dispatchWindow('pagehide', { persisted: true });
  assert.equal(env.window[`ga-disable-${ID}`], false);
  assert.equal(env.eventOptions.get('pageshow').capture, true);
  env.stored.set(KEY, choice('rejected', NOW)); // Aucun événement storage sur la page gelée.
  env.dispatchWindow('pageshow', { persisted: true });
  assert.equal(env.window[`ga-disable-${ID}`], true);
  assert.equal(env.reloads, 1);
  env.window.atelierAnalytics.quizStarted();
  assert.equal(events(env).length, 0);
  assert.match(env.nodes.get('analytics-status').textContent, /refusée/);
});

test('Un retour du cache avec accord valide ne recharge pas la balise ni la page_view', () => {
  const env = environment({ storage: { [KEY]: choice('accepted') } });
  env.dispatchWindow('pagehide', { persisted: true });
  env.dispatchWindow('pageshow', { persisted: true });
  assert.equal(env.window[`ga-disable-${ID}`], false);
  assert.equal(env.reloads, 0);
  assert.equal(env.scripts.length, 1);
  assert.equal(events(env, 'page_view').length, 1);
  env.window.atelierAnalytics.quizStarted();
  assert.equal(events(env, 'quiz_start').length, 1);
});

test('Un accord expiré pendant la mise en cache ne reprend pas à la restauration', () => {
  const env = environment({ storage: { [KEY]: choice('accepted') } });
  env.dispatchWindow('pagehide', { persisted: true });
  env.stored.set(KEY, choice('accepted', NOW - RETENTION));
  env.dispatchWindow('pageshow', { persisted: true });
  assert.equal(env.window[`ga-disable-${ID}`], true);
  assert.equal(env.reloads, 1);
  assert.equal(env.nodes.get('analytics-consent').hidden, false);
});

test('Une page redevenue visible relit le consentement sans attendre un nouvel événement quiz', () => {
  const env = environment({ storage: { [KEY]: choice('accepted') } });
  env.visibility('hidden');
  env.stored.set(KEY, choice('rejected', NOW));
  env.visibility('visible');
  assert.equal(env.window[`ga-disable-${ID}`], true);
  assert.equal(env.reloads, 1);
  const blocked = environment({ storageBlocked: true });
  blocked.clicks('analytics-accept');
  blocked.visibility('hidden');
  blocked.visibility('visible');
  assert.equal(blocked.reloads, 0);
  assert.equal(blocked.window[`ga-disable-${ID}`], false);
});

test('Les pages de catalogue ne fabriquent pas de contexte de quiz', () => {
  const env = environment({ config: { level: undefined, quiz_id: undefined, quiz_theme: undefined } });
  env.clicks('analytics-accept');
  env.window.atelierAnalytics.quizStarted();
  env.window.atelierAnalytics.quizCompleted();
  assert.deepEqual(events(env).map((item) => item[1]), ['page_view']);
  assert.deepEqual(events(env)[0][2], {
    page_location: `${ORIGIN}${BASE}/quiz/4e-temps-recit/`, page_referrer: '',
  });
  const level = environment({ config: { level: 'seconde', quiz_id: '', quiz_theme: '' } });
  level.clicks('analytics-accept');
  assert.equal(events(level)[0][2].education_level, 'seconde');
  assert.equal(events(level)[0][2].quiz_id, undefined);
  assert.equal(level.commands().find((item) => item[0] === 'config')[2].page_title, 'Quiz de seconde · L’atelier de Madame Daadoun');
});

test('Les états chargement et chargé ne prétendent jamais confirmer une réception GA4', () => {
  const env = environment();
  assert.equal(env.nodes.get('analytics-status').textContent, 'Facultatif. Ton choix reste modifiable en bas de page.');
  env.clicks('analytics-accept');
  assert.match(env.nodes.get('analytics-status').textContent, /Chargement de la balise en cours/);
  assert.equal(env.nodes.get('analytics-accept').textContent, 'Accepter');
  env.scripts[0].onload();
  assert.match(env.nodes.get('analytics-status').textContent, /Balise chargée\. Les rapports peuvent mettre quelques minutes à s’actualiser\./);
  assert.doesNotMatch(env.nodes.get('analytics-status').textContent, /reçu|réception|collecté|envoyé/);
  assert.equal(env.runTimer(20000), false);
  assert.equal(env.reloads, 0);
});

test('Après une erreur, Réessayer recharge uniquement sur action explicite et prévient avant', () => {
  const env = environment();
  env.clicks('analytics-accept');
  const savedChoice = env.stored.get(KEY);
  env.scripts[0].onerror();
  assert.equal(env.window[`ga-disable-${ID}`], true);
  assert.match(env.nodes.get('analytics-status').textContent, /échoué ou a été bloqué/);
  assert.match(env.nodes.get('analytics-status').textContent, /Réessayer ou refuser recharge la page et recommence le quiz/);
  assert.equal(env.nodes.get('analytics-accept').textContent, 'Réessayer');
  assert.equal(env.runTimer(20000), false);
  assert.equal(env.reloads, 0);
  env.clicks('analytics-settings');
  assert.equal(env.reloads, 0);
  env.clicks('analytics-accept');
  assert.equal(env.reloads, 1);
  assert.equal(env.scripts.length, 1);
  assert.equal(env.scripts[0].removed, true);
  assert.equal(env.stored.get(KEY), savedChoice);
  env.scripts[0].onload();
  env.window.atelierAnalytics.quizStarted();
  assert.equal(env.commands().length, 0);
  assert.doesNotMatch(env.nodes.get('analytics-status').textContent, /Balise chargée/);
});

test('Après 20 secondes sans réponse, le chargement reste indéterminé et peut finir', () => {
  const env = environment();
  env.clicks('analytics-accept');
  assert.equal(env.runTimer(20000), true);
  assert.match(env.nodes.get('analytics-status').textContent, /pas encore confirmé/);
  assert.doesNotMatch(env.nodes.get('analytics-status').textContent, /échoué|Balise chargée|reçu/);
  assert.equal(env.nodes.get('analytics-accept').textContent, 'Réessayer');
  assert.equal(env.window[`ga-disable-${ID}`], false);
  assert.equal(env.reloads, 0);
  env.scripts[0].onload();
  assert.match(env.nodes.get('analytics-status').textContent, /Balise chargée/);
  assert.equal(env.nodes.get('analytics-accept').textContent, 'Accepter');
  assert.equal(env.scripts.length, 1);
  assert.equal(env.reloads, 0);
});

test('Un chargement indéterminé peut être réessayé explicitement sans créer une seconde balise', () => {
  const env = environment();
  env.clicks('analytics-accept');
  env.runTimer(20000);
  assert.match(env.nodes.get('analytics-status').textContent, /Réessayer ou refuser recharge la page et recommence le quiz/);
  env.clicks('analytics-accept');
  assert.equal(env.reloads, 1);
  assert.equal(env.scripts.length, 1);
  assert.equal(env.window[`ga-disable-${ID}`], true);
  assert.equal(env.commands().length, 0);
});

test('Un départ rapide laisse terminer le transport autorisé mais suspend les nouveaux hooks', () => {
  const env = environment();
  env.clicks('analytics-accept');
  env.window.atelierAnalytics.quizStarted();
  const beforeDeparture = env.commands();
  env.dispatchWindow('pagehide', { persisted: false });
  assert.equal(env.window[`ga-disable-${ID}`], false);
  env.window.atelierAnalytics.quizCompleted();
  assert.deepEqual(env.commands(), beforeDeparture);
  assert.equal(env.reloads, 0);
});

test('Les exceptions du tag restent isolées du parcours du quiz', () => {
  const insertion = environment({ appendBlocked: true });
  assert.doesNotThrow(() => insertion.clicks('analytics-accept'));
  assert.match(insertion.nodes.get('analytics-status').textContent, /quiz reste utilisable/);
  const env = environment();
  env.clicks('analytics-accept');
  env.window.dataLayer.push = () => { throw new Error('Traitement du tag indisponible'); };
  assert.doesNotThrow(() => env.window.atelierAnalytics.quizStarted());
  assert.doesNotThrow(() => env.window.atelierAnalytics.quizCompleted());
  assert.doesNotThrow(() => env.window.atelierAnalytics.resetAttempt());
  assert.equal(env.window[`ga-disable-${ID}`], true);
  assert.match(env.nodes.get('analytics-status').textContent, /quiz reste utilisable/);
});
