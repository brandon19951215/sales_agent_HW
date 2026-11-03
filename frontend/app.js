const form = document.querySelector('#analysis-form');
const promptInput = document.querySelector('#prompt');
const submitButton = document.querySelector('#analyze');
const buttonLabel = document.querySelector('#button-label');
const resultCard = document.querySelector('#result-card');
const statusText = document.querySelector('#status');
const badge = document.querySelector('#result-badge');
const emptyState = document.querySelector('#empty-state');
const answer = document.querySelector('#answer');
const errorBox = document.querySelector('#error');
const note = document.querySelector('#result-note');

document.querySelectorAll('[data-period]').forEach(button => {
  button.addEventListener('click', () => {
    promptInput.value = `Compare Singapore's sales for ${button.dataset.period} with target and calculate the percentage variance.`;
    promptInput.setCustomValidity('');
    promptInput.focus();
  });
});

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (submitButton.disabled) return;
  const prompt = promptInput.value.trim();
  if (!prompt) {
    promptInput.setCustomValidity('Enter a sales question first.');
    promptInput.reportValidity();
    return;
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 100000);
  submitButton.disabled = true;
  buttonLabel.textContent = 'Analyzing…';
  resultCard.setAttribute('aria-busy', 'true');
  badge.textContent = 'Working';
  statusText.textContent = 'Your agent is checking sales, targets and variance. This may take a moment.';
  emptyState.hidden = true;
  answer.hidden = true;
  errorBox.hidden = true;
  note.hidden = true;
  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({prompt}),
      signal: controller.signal,
    });
    let data;
    try { data = await response.json(); }
    catch { throw new Error('The server returned an unreadable response. Please try again.'); }
    if (!response.ok) {
      throw new Error(typeof data.detail === 'string' ? data.detail : 'The request could not be completed. Check your question and try again.');
    }
    if (typeof data.answer !== 'string' || !data.answer.trim()) throw new Error('The agent returned an empty answer. Please try again.');
    // Render as text so model output cannot inject HTML into the page.
    answer.textContent = data.answer;
    answer.hidden = false;
    note.hidden = false;
    badge.textContent = 'Complete';
    statusText.textContent = 'Analysis complete.';
  } catch (error) {
    errorBox.textContent = error.name === 'AbortError'
      ? 'The request timed out. Please try again.'
      : error instanceof TypeError
        ? 'Cannot reach the server. Check that the frontend and backend are running, then try again.'
        : error.message;
    errorBox.hidden = false;
    badge.textContent = 'Try again';
    statusText.textContent = '';
  } finally {
    clearTimeout(timer);
    submitButton.disabled = false;
    buttonLabel.textContent = 'Analyze sales';
    resultCard.setAttribute('aria-busy', 'false');
  }
});
promptInput.addEventListener('input', () => promptInput.setCustomValidity(''));
