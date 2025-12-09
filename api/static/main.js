const chatLog = document.getElementById('chatLog');
const sourcesEl = document.getElementById('sources');
const questionEl = document.getElementById('question');
const useRagEl = document.getElementById('useRag');
const statusEl = document.getElementById('status');
const ocrDebugEl = document.getElementById('ocrDebug');
const imageInput = document.getElementById('imageInput');
const dropzone = document.getElementById('dropzone');
const imagePreview = document.getElementById('imagePreview');
const chooseFile = document.getElementById('chooseFile');
const history = [];

function addMessage(role, text) {
    const bubble = document.createElement('div');
    bubble.className = 'bubble ' + (role === 'user' ? 'user' : 'bot');
    bubble.textContent = text;
    chatLog.appendChild(bubble);
    chatLog.scrollTop = chatLog.scrollHeight;
}

function addImageMessage(role, src) {
    const bubble = document.createElement('div');
    bubble.className = 'bubble ' + (role === 'user' ? 'user' : 'bot');
    const img = document.createElement('img');
    img.src = src;
    bubble.appendChild(img);
    chatLog.appendChild(bubble);
    chatLog.scrollTop = chatLog.scrollHeight;
}

async function send() {
    const q = questionEl.value.trim();
    const file = imageInput.files[0];
    if (!q && !file) return;

    addMessage('user', q || '(이미지 업로드)'); 
    history.push(q || '이미지 업로드');
    questionEl.value = '';
    statusEl.textContent = '생각 중...';
    sourcesEl.textContent = '생각 중...';

    try {
        // Show image in chat for user if provided
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => addImageMessage('user', e.target.result);
            reader.readAsDataURL(file);
        }

        if (file) {
            const form = new FormData();
            form.append('file', file);
            form.append('question', q);
            form.append('use_rag', useRagEl.checked);
            const resp = await fetch('/image-query', { method: 'POST', body: form });
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            const data = await resp.json();
            addMessage('bot', data.answer || '(응답 없음)');
            statusEl.textContent = '';
            if (data.ocr_text) {
                addMessage('bot', '[OCR]\n' + data.ocr_text);
                ocrDebugEl.textContent = data.ocr_text;
            } else {
                ocrDebugEl.textContent = '(OCR 결과 없음)';
            }
            renderSources(data.source_documents);
        } else {
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
        }
    } catch (err) {
        statusEl.innerHTML = '<span class="error">오류: ' + err.message + '</span>';
    } finally {
        imageInput.value = '';
        imagePreview.innerHTML = '';
        if (!file) {
            ocrDebugEl.textContent = '이미지 업로드 시 OCR 결과가 여기에 표시됩니다.';
        }
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

function handleFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        // Support multiple thumbnails (though we keep single selection)
        const thumb = document.createElement('div');
        thumb.className = 'thumb';
        const img = document.createElement('img');
        img.src = e.target.result;
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-btn';
        removeBtn.textContent = '×';
        removeBtn.addEventListener('click', () => {
            imagePreview.innerHTML = '';
            imageInput.value = '';
            ocrDebugEl.textContent = '이미지 업로드 시 OCR 결과가 여기에 표시됩니다.';
        });
        thumb.appendChild(img);
        thumb.appendChild(removeBtn);
        imagePreview.innerHTML = '';
        imagePreview.appendChild(thumb);
    };
    reader.readAsDataURL(file);
}

dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragging');
});

dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragging');
});

dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragging');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        const dt = new DataTransfer();
        dt.items.add(e.dataTransfer.files[0]);
        imageInput.files = dt.files;
        handleFile(e.dataTransfer.files[0]);
    }
});

chooseFile.addEventListener('click', () => imageInput.click());
imageInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
        handleFile(e.target.files[0]);
    }
});

document.getElementById('sendBtn').addEventListener('click', send);
questionEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        send();
    }
});
