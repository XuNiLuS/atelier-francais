/* Correction locale. Le parcours de cet essai reste uniquement dans cet onglet. */
'use strict';

const quiz = JSON.parse(document.getElementById('quiz-data').textContent);
const questions = quiz.questions;
const form = document.getElementById('quiz-form');
const panels = [...document.querySelectorAll('.question-panel')];
const navigation = [...document.querySelectorAll('.question-nav')];
const previousButton = document.getElementById('previous-button');
const checkButton = document.getElementById('check-button');
const nextButton = document.getElementById('next-button');
const submitButton = document.getElementById('submit-button');
const message = document.getElementById('form-message');
// Un résultat enregistré fige la première réponse vérifiée jusqu'au prochain essai.
const verifiedAnswers = new Map();
let currentIndex = 0;
let checking = false;
let submitting = false;
let checkFailed = false;

function selectedAnswer(question) {
  return form.querySelector(`input[name="question-${question.id}"]:checked`)?.value;
}

function updateProgress() {
  document.getElementById('answered-count').textContent = verifiedAnswers.size;
  document.getElementById('quiz-progress').value = verifiedAnswers.size;
  navigation.forEach((button, index) => {
    const question = questions[index];
    const verified = verifiedAnswers.has(question.id);
    const draft = !verified && Boolean(selectedAnswer(question));
    button.classList.toggle('answered', verified);
    button.classList.toggle('draft', draft);
    const status = verified ? 'réponse vérifiée' : draft ? 'choix à vérifier' : 'sans réponse';
    button.setAttribute('aria-label', `Question ${index + 1}, ${status}`);
  });
}

function updateControls() {
  const busy = checking || submitting;
  const verified = verifiedAnswers.has(questions[currentIndex].id);
  const lastQuestion = currentIndex === questions.length - 1;
  previousButton.disabled = busy || currentIndex === 0;
  navigation.forEach((button) => { button.disabled = busy; });
  checkButton.hidden = verified;
  checkButton.disabled = busy;
  checkButton.textContent = checking ? 'Vérification…' : checkFailed ? 'Réessayer' : 'Vérifier ma réponse';
  nextButton.hidden = !verified || lastQuestion;
  nextButton.disabled = busy;
  submitButton.hidden = !verified || !lastQuestion;
  submitButton.disabled = busy;
  submitButton.textContent = submitting ? 'Calcul du bilan…' : 'Voir mon bilan';
  panels.forEach((panel, index) => {
    panel.querySelector('fieldset').disabled = busy || verifiedAnswers.has(questions[index].id);
  });
  if (busy) form.setAttribute('aria-busy', 'true');
  else form.removeAttribute('aria-busy');
}

function showQuestion(index, focus = true) {
  if (checking || submitting || index < 0 || index >= questions.length) return;
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
  document.getElementById('tense-tag').textContent = questions[index].label;
  document.getElementById('question-title').textContent = questions[index].prompt;
  message.textContent = '';
  checkFailed = false;
  updateControls();
  if (focus) document.getElementById('question-title').focus();
}

navigation.forEach((button, index) => button.addEventListener('click', () => showQuestion(index)));
previousButton.addEventListener('click', () => showQuestion(currentIndex - 1));
nextButton.addEventListener('click', () => showQuestion(currentIndex + 1));
form.addEventListener('change', () => {
  checkFailed = false;
  message.textContent = '';
  updateProgress();
  updateControls();
});

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function resultFor(question, selected) {
  return {
    id: question.id,
    selected,
    correct_answer: question.answer,
    is_correct: selected === question.answer,
    explanation: question.explanation,
  };
}

function correctionMatches(question, result, selected) {
  return result && result.id === question.id
    && result.selected === selected
    && question.options.some((option) => option.id === result.correct_answer)
    && typeof result.is_correct === 'boolean'
    && result.is_correct === (selected === result.correct_answer)
    && typeof result.explanation === 'string' && result.explanation.trim();
}


function renderFeedback(question, result) {
  const panel = panels[questions.indexOf(question)];
  const feedback = document.getElementById(`feedback-${question.id}`);
  const correct = question.options.find((option) => option.id === result.correct_answer);
  feedback.classList.toggle('incorrect', !result.is_correct);
  const status = element('h3', 'feedback-status', result.is_correct ? '✓ Bonne réponse !' : 'À revoir');
  const answer = element('p', 'feedback-answer');
  answer.append(element('strong', '', 'Bonne réponse : '), document.createTextNode(`${correct.id.toUpperCase()}. ${correct.label}`));
  feedback.replaceChildren(status, answer, element('p', 'feedback-explanation', result.explanation));
  feedback.hidden = false;
  panel.querySelectorAll('.option').forEach((option) => {
    const value = option.querySelector('input').value;
    const isCorrect = value === result.correct_answer;
    const isWrong = value === result.selected && !result.is_correct;
    option.classList.toggle('correct-option', isCorrect);
    option.classList.toggle('incorrect-option', isWrong);
    const symbol = option.querySelector('.option-check');
    symbol.textContent = isWrong ? '×' : '✓';
  });
}

function checkAnswer() {
  const question = questions[currentIndex];
  if (checking || submitting || verifiedAnswers.has(question.id)) return;
  const selected = selectedAnswer(question);
  if (!selected) {
    message.textContent = 'Choisis une réponse avant de la vérifier.';
    panels[currentIndex].querySelector('input').focus();
    return;
  }
  checking = true;
  checkFailed = false;
  message.textContent = '';
  updateControls();
  try {
    const result = resultFor(question, selected);
    if (!correctionMatches(question, result, selected)) {
      throw new Error('La correction reçue est incomplète. Ton choix est conservé ; réessaie.');
    }
    renderFeedback(question, result);
    verifiedAnswers.set(question.id, result);
    updateProgress();
    // La mesure facultative ne doit jamais interrompre une correction.
    try {
      if (verifiedAnswers.size === 1) window.atelierAnalytics?.quizStarted();
      if (verifiedAnswers.size === questions.length) window.atelierAnalytics?.quizCompleted();
    } catch { /* Le quiz reste utilisable si les statistiques sont indisponibles. */ }
  } catch (error) {
    checkFailed = true;
    message.textContent = error.message || 'Un problème empêche la correction. Recharge le quiz.';
  } finally {
    checking = false;
    updateControls();
  }
  if (verifiedAnswers.has(question.id)) document.getElementById(`feedback-${question.id}`).focus();
  else checkButton.focus();
}

function renderResults(payload) {
  const list = document.getElementById('correction-list');
  list.replaceChildren();
  const scoresByTopic = new Map();

  payload.results.forEach((result) => {
    const question = questions.find((item) => item.id === result.id);
    const score = scoresByTopic.get(question.label) || { correct: 0, total: 0 };
    score.total += 1;
    if (result.is_correct) score.correct += 1;
    scoresByTopic.set(question.label, score);

    const card = element('article', `correction-card${result.is_correct ? '' : ' incorrect'}`);
    const meta = element('div', 'correction-meta');
    meta.append(element('span', '', `QUESTION ${String(questions.indexOf(question) + 1).padStart(2, '0')} · ${question.label}`));
    meta.append(element('span', 'answer-status', result.is_correct ? '✓ Bonne réponse' : 'À revoir'));
    const sentence = element('p', 'correction-sentence');
    sentence.append(document.createTextNode(question.before), element('mark', '', question.focus), document.createTextNode(question.after));
    card.append(meta, element('h4', 'correction-prompt', question.prompt), sentence);
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
  if (payload.score === payload.total) feedback = 'Tout juste ! Tu as su observer les phrases et analyser les indices.';
  else if (payload.score / payload.total >= 0.75) feedback = 'De bons repères ! Lis les explications pour comprendre les quelques pièges.';
  else if (payload.score / payload.total >= 0.5) feedback = 'Tu es sur la bonne voie. Appuie-toi sur les indices de chaque phrase pour progresser.';
  else feedback = 'Chaque essai aide à progresser. Prends le temps de lire les explications, puis réessaie.';
  document.getElementById('result-message').textContent = feedback;
  const tenseScores = document.getElementById('tense-scores');
  tenseScores.replaceChildren();
  document.getElementById('topic-breakdown').open = scoresByTopic.size <= 6;
  for (const [tense, score] of scoresByTopic) {
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

function submitAnswers() {
  if (checking || submitting) return;
  const missingIndex = questions.findIndex((question) => !verifiedAnswers.has(question.id));
  if (missingIndex !== -1) {
    showQuestion(missingIndex);
    message.textContent = 'Il reste des réponses à vérifier. Vérifie celle-ci, puis les suivantes, avant de voir ton bilan.';
    return;
  }
  // Calculer le bilan à partir des premières réponses vérifiées.
  const answers = Object.fromEntries([...verifiedAnswers].map(([id, result]) => [String(id), result.selected]));
  submitting = true;
  message.textContent = '';
  updateControls();
  try {
    const results = questions.map((question) => resultFor(question, answers[String(question.id)]));
    const payload = { results, total: questions.length, score: results.filter((result) => result.is_correct).length };
    const validResults = Array.isArray(payload.results)
      && payload.results.length === questions.length
      && new Set(payload.results.map((result) => result.id)).size === questions.length
      && payload.results.every((result) => {
        const question = questions.find((item) => item.id === result.id);
        return question && correctionMatches(question, result, answers[String(result.id)]);
      });
    if (!validResults || payload.total !== questions.length
      || payload.score !== payload.results.filter((result) => result.is_correct).length) {
      throw new Error('Le bilan reçu est incomplet. Tes réponses sont conservées ; réessaie.');
    }
    renderResults(payload);
  } catch (error) {
    message.textContent = error.message || 'Un problème empêche la correction. Recharge le quiz.';
  } finally {
    submitting = false;
    updateControls();
  }
  if (document.getElementById('results').hidden) submitButton.focus();
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  if (checking || submitting) return;
  if (event.submitter === submitButton
    || (currentIndex === questions.length - 1 && verifiedAnswers.has(questions[currentIndex].id))) {
    submitAnswers();
  } else {
    checkAnswer();
  }
});

document.getElementById('restart-button').addEventListener('click', () => {
  form.reset();
  verifiedAnswers.clear();
  try { window.atelierAnalytics?.resetAttempt(); } catch { /* Mesure facultative. */ }
  checking = false;
  submitting = false;
  checkFailed = false;
  panels.forEach((panel) => {
    const feedback = panel.querySelector('.answer-feedback');
    feedback.replaceChildren();
    feedback.hidden = true;
    feedback.classList.remove('incorrect');
    panel.querySelectorAll('.option').forEach((option) => {
      option.classList.remove('correct-option', 'incorrect-option');
      option.querySelector('.option-check').textContent = '✓';
    });
  });
  updateProgress();
  document.getElementById('correction-list').replaceChildren();
  document.getElementById('tense-scores').replaceChildren();
  document.getElementById('score-value').textContent = '0';
  document.getElementById('result-message').textContent = '';
  document.getElementById('results').hidden = true;
  document.getElementById('quiz-workspace').hidden = false;
  document.querySelector('.skip-link').href = '#question-title';
  document.querySelector('.skip-link').textContent = 'Aller à la question';
  showQuestion(0);
});

updateProgress();
showQuestion(0, false);
