const chatLog = document.getElementById('chatLog');
const sourcesEl = document.getElementById('sources');
const questionEl = document.getElementById('question');
const useRagEl = document.getElementById('useRag');
const statusEl = document.getElementById('status');
const history = [];

function addMessage(role, text) {
    const bubble = document.createElement('div');
    bubble.className = 'bubble ' + (role === 'user' ? 'user' : 'bot');
    bubble.textContent = text;
    chatLog.appendChild(bubble);
    chatLog.scrollTop = chatLog.scrollHeight;
}

async function send() {
    const q = questionEl.value.trim();
    if (!q) return;

    addMessage('user', q);
    history.push(q);
    questionEl.value = '';
    statusEl.textContent = '생각 중...';
    sourcesEl.textContent = '생각 중...';

    try {
        const resp = await fetch('/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: q,
                use_rag: useRagEl.checked,
                chat_history: history
            })
        });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const data = await resp.json();
        addMessage('bot', data.answer || '(응답 없음)');
        statusEl.textContent = '';
        renderSources(data.source_documents);
    } catch (err) {
        statusEl.innerHTML = '<span class="error">오류: ' + err.message + '</span>';
    }
}

function renderSources(docs) {
    if (docs && docs.length) {
        sourcesEl.innerHTML = docs.map((d, idx) => {
            const title = d.title || '제목 없음';
            const url = d.url ? `<a href="${d.url}" target="_blank">${d.url}</a>` : '';
            const score = d.score !== null && d.score !== undefined ? ` (score: ${d.score.toFixed ? d.score.toFixed(3) : d.score})` : '';
            return `<div><strong>[${idx + 1}] ${title}${score}</strong><br>${url}</div>`;
        }).join('<hr />');
    } else {
        sourcesEl.textContent = useRagEl.checked ? '참고 문서 없음' : 'RAG 미사용 (임베딩 off)';
    }
}

document.getElementById('sendBtn').addEventListener('click', send);
questionEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        send();
    }
});
