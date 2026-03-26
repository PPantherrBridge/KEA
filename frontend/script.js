const chatBox = document.getElementById('chat-box');
const form = document.getElementById('chat-form');
const questionInput = document.getElementById('question-input');
const loading = document.getElementById('loading');

function addMessage(sender, text, sources = []) {
  const div = document.createElement('div');
  div.className = `msg ${sender}`;
  div.innerHTML = `<strong>${sender === 'user' ? 'You' : 'Bot'}:</strong> ${text}`;

  if (sender === 'bot' && sources.length > 0) {
    const srcDiv = document.createElement('div');
    srcDiv.className = 'sources';
    srcDiv.innerHTML = `Sources: ${sources.map(s => `<a href="${s.url}" target="_blank">${s.url}</a>`).join(' | ')}`;
    div.appendChild(srcDiv);
  }

  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;

  addMessage('user', question);
  questionInput.value = '';
  loading.classList.remove('hidden');

  try {
    const res = await fetch('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });

    const data = await res.json();
    if (!res.ok) {
      addMessage('bot', data.error || 'Request failed.');
    } else {
      addMessage('bot', data.answer, data.sources || []);
    }
  } catch (err) {
    addMessage('bot', `Network error: ${err.message}`);
  } finally {
    loading.classList.add('hidden');
  }
});
