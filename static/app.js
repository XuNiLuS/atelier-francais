/* Le serveur calcule le score. Le navigateur gère seulement le parcours. */
'use strict';

const questions = JSON.parse(document.getElementById('quiz-data').textContent);
const form = document.getElementById('quiz-form');
const panels = [...document.querySelectorAll('.question-panel')];
const navigation = [...document.querySelectorAll('.question-nav')];
const previousButton = document.getElementById('previous-button');
const nextButton = document.getElementById('next-button');
const submitButton = document.getElementById('submit-button');
const message = document.getElementById('form-message');
let currentIndex = 0;
let submitting = false;

function readAnswers() {
  const answers = {};
  for (const question of questions) {
    const checked = form.querySelector(`input[name="question-${question.id}"]:checked`);
    if (checked) answers[String(question.id)] = checked.value;
  }
  return answers;
}

function updateProgress() {
  const answers = readAnswers();
  document.getElementById('answered-count').textContent = Object.keys(answers).length;
  document.getElementById('quiz-progress').value = Object.keys(answers).length;
  navigation.forEach((button, index) => {
    const answered = Object.hasOwn(answers, String(questions[index].id));
    button.classList.toggle('answered', answered);
    button.setAttribute('aria-label', `Question ${index + 1}, ${answered ? 'répondue' : 'sans réponse'}`);
  });
}

function showQuestion(index, focus = true) {
  if (submitting || index < 0 || index >= questions.length) return;
  currentIndex = index;
  panels.forEach((panel, panelIndex) => { panel.hidden = panelIndex !== index; });
  navigation.forEach((button, buttonIndex) => {
    const isCurrent = buttonIndex === index;
    button.classList.toggle('current', isCurrent);
    if (isCurrent) button.setAttribute('aria-current', 'step');
    else button.removeAttribute('aria-current');
  });
  const position = `${String(index + 1).padStart(2, '0')} / ${questions.length}`;
  document.getElementById('question-position').textContent = `QUESTION ${position}`;
  document.getElementById('question-counter').textContent = position;
  document.getElementById('tense-tag').textContent = questions[index].tense;
  previousButton.disabled = index === 0;
  nextButton.hidden = index === questions.length - 1;
  submitButton.hidden = index !== questions.length - 1;
  message.textContent = '';
  if (focus) document.getElementById('question-title').focus({ preventScroll: false });
}

navigation.forEach((button, index) => button.addEventListener('click', () => showQuestion(index)));
previousButton.addEventListener('click', () => showQuestion(currentIndex - 1));
nextButton.addEventListener('click', () => showQuestion(currentIndex + 1));
form.addEventListener('change', () => {
  updateProgress();
  message.textContent = '';
});

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderResults(payload) {
  const list = document.getElementById('correction-list');
  list.replaceChildren();
  const scoresByTense = new Map();

  payload.results.forEach((result) => {
    const question = questions.find((item) => item.id === result.id);
    const score = scoresByTense.get(question.tense) || { correct: 0, total: 0 };
    score.total += 1;
    if (result.is_correct) score.correct += 1;
    scoresByTense.set(question.tense, score);

    const card = element('article', `correction-card${result.is_correct ? '' : ' incorrect'}`);
    const meta = element('div', 'correction-meta');
    meta.append(element('span', '', `QUESTION ${String(questions.indexOf(question) + 1).padStart(2, '0')} · ${question.tense}`));
    meta.append(element('span', 'answer-status', result.is_correct ? '✓ Bonne réponse' : 'À revoir'));
    const sentence = element('p', 'correction-sentence');
    sentence.append(document.createTextNode(question.before), element('mark', '', question.verb), document.createTextNode(question.after));
    card.append(meta, sentence);
    const selected = question.options.find((option) => option.id === result.selected);
    const correct = question.options.find((option) => option.id === result.correct_answer);
    if (!result.is_correct) card.append(element('p', 'correction-answer wrong', `Ta réponse : ${selected.label}`));
    const answer = element('p', 'correction-answer');
    answer.append(element('strong', '', 'Bonne réponse : '), document.createTextNode(correct.label));
    card.append(answer, element('p', 'correction-explanation', result.explanation));
    list.append(card);
  });

  document.getElementById('score-value').textContent = payload.score;
  let feedback;
  if (payload.score === payload.total) feedback = 'Tout juste ! Tu as bien repéré le rôle des temps dans le récit.';
  else if (payload.score >= 15) feedback = 'De bons repères ! Lis les explications pour comprendre les quelques pièges.';
  else if (payload.score >= 10) feedback = 'Tu es sur la bonne voie. Appuie-toi sur les indices de chaque phrase pour progresser.';
  else feedback = 'Chaque essai aide à progresser. Prends le temps de lire les explications, puis réessaie.';
  document.getElementById('result-message').textContent = feedback;
  const tenseScores = document.getElementById('tense-scores');
  tenseScores.replaceChildren();
  for (const [tense, score] of scoresByTense) {
    const item = element('div', 'tense-score');
    item.append(element('span', '', tense), element('strong', '', `${score.correct} / ${score.total}`));
    tenseScores.append(item);
  }
  document.getElementById('quiz-workspace').hidden = true;
  document.getElementById('results').hidden = false;
  document.querySelector('.skip-link').href = '#results-title';
  document.querySelector('.skip-link').textContent = 'Aller à la correction';
  document.getElementById('results-title').focus();
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (submitting) return;
  const answers = readAnswers();
  const missingIndex = questions.findIndex((question) => !Object.hasOwn(answers, String(question.id)));
  if (missingIndex !== -1) {
    showQuestion(missingIndex);
    message.textContent = 'Il reste des questions sans réponse. Choisis une réponse pour chacune avant la correction.';
    return;
  }
  submitting = true;
  submitButton.disabled = true;
  submitButton.textContent = 'Correction en cours…';
  form.setAttribute('aria-busy', 'true');
  // Figer les réponses pendant la correction pour garder le score cohérent.
  form.querySelectorAll('input').forEach((input) => { input.disabled = true; });
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers }),
      signal: controller.signal,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'La correction est indisponible pour le moment. Réessaie.');
    renderResults(payload);
  } catch (error) {
    message.textContent = error.name === 'AbortError' || error instanceof TypeError || error instanceof SyntaxError
      ? 'Impossible de joindre la correction. Tes réponses sont conservées sur cette page ; réessaie dans un instant.'
      : error.message;
    submitButton.focus();
  } finally {
    clearTimeout(timeout);
    submitting = false;
    submitButton.disabled = false;
    submitButton.textContent = 'Voir ma correction';
    form.removeAttribute('aria-busy');
    form.querySelectorAll('input').forEach((input) => { input.disabled = false; });
  }
});

document.getElementById('restart-button').addEventListener('click', () => {
  form.reset();
  updateProgress();
  document.getElementById('results').hidden = true;
  document.getElementById('quiz-workspace').hidden = false;
  document.querySelector('.skip-link').href = '#question-title';
  document.querySelector('.skip-link').textContent = 'Aller à la question';
  showQuestion(0);
});
