const fileUpload = document.getElementById('file-upload');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const chatHistory = document.getElementById('chat-history');
const docUl = document.getElementById('doc-ul');
const docTitle = document.getElementById('current-doc-title');
const docMeta = document.getElementById('doc-meta');

let currentDocId = null;

// Initialize
function init() {
    fileUpload.addEventListener('change', handleUpload);
    chatForm.addEventListener('submit', handleQuery);
}

function appendMessage(sender, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;
    const contentDiv = document.createElement('div');
    contentDiv.className = 'msg-content';
    contentDiv.textContent = text;
    msgDiv.appendChild(contentDiv);
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function appendLoader() {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message bot loader`;
    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
    msgDiv.appendChild(indicator);
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    return msgDiv;
}

async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    // UI Updates
    chatInput.disabled = true;
    sendBtn.disabled = true;
    docTitle.textContent = "Uploading & Analyzing...";
    docMeta.textContent = file.name;
    
    // Add loader in chat
    const loader = appendLoader();

    const formData = new FormData();
    formData.append('document', file);

    try {
        const res = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        
        loader.remove();

        if (res.ok) {
            currentDocId = data.doc_id;
            
            // Add to sidebar
            const li = document.createElement('li');
            li.className = 'doc-item active';
            li.textContent = data.filename;
            docUl.appendChild(li);

            // Update Header
            docTitle.textContent = data.filename;
            docMeta.textContent = `${data.word_count} words | Sections Detected: FACT (${data.sections.FACTS}), ARG (${data.sections.ARGUMENTS}), JUDGE (${data.sections.JUDGMENT})`;

            // Enable chat
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();

            // Print summary
            let summaryText = `Document loaded successfully.\n\n`;
            if (data.summaries) {
                if (data.summaries.ARGUMENTS !== "No content detected.") {
                     summaryText += `📌 ARGUMENTS SUMMARY:\n${data.summaries.ARGUMENTS}\n\n`;
                }
                if (data.summaries.JUDGMENT !== "No content detected.") {
                     summaryText += `📌 JUDGMENT SUMMARY:\n${data.summaries.JUDGMENT}`;
                }
            }
            appendMessage('bot', summaryText);
        } else {
            docTitle.textContent = "Upload Failed";
            appendMessage('bot', `Error: ${data.error}`);
        }
    } catch (err) {
        loader.remove();
        docTitle.textContent = "Error";
        appendMessage('bot', "Connection error during upload.");
    }
}

async function handleQuery(e) {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (!query || !currentDocId) return;

    // Append User UI
    appendMessage('user', query);
    chatInput.value = '';
    
    const loader = appendLoader();
    chatInput.disabled = true;
    sendBtn.disabled = true;

    try {
        const res = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ doc_id: currentDocId, query: query })
        });
        const data = await res.json();
        
        loader.remove();
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();

        if (res.ok) {
            appendMessage('bot', data.answer);
        } else {
            appendMessage('bot', `Error: ${data.error}`);
        }
    } catch (err) {
        loader.remove();
        chatInput.disabled = false;
        sendBtn.disabled = false;
        appendMessage('bot', "Connection error processing your question.");
    }
}

init();
