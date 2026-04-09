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
    return msgDiv;
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
                const botMsg = appendMessage('bot', data.answer);

                // If we received selection/process info, add buttons to view them
                if (data.selected_sentences || data.process) {
                    const controls = document.createElement('div');
                    controls.className = 'msg-controls';

                    const btn1 = document.createElement('button');
                    btn1.className = 'mini-btn';
                    btn1.textContent = 'View Selected Sentences';

                    const btn2 = document.createElement('button');
                    btn2.className = 'mini-btn';
                    btn2.textContent = 'View Processing Details';

                    controls.appendChild(btn1);
                    controls.appendChild(btn2);
                    botMsg.appendChild(controls);

                    // Modal elements
                    const sentencesModal = document.getElementById('sentences-modal');
                    const processModal = document.getElementById('process-modal');
                    const sentencesBody = document.getElementById('sentences-body');
                    const processBody = document.getElementById('process-body');

                    function openSentences() {
                        // populate sentencesBody
                        sentencesBody.innerHTML = '';
                        const list = data.selected_sentences || [];
                        if (list.length === 0) {
                            sentencesBody.textContent = 'No sentences met the relevance threshold.';
                        } else {
                            list.forEach((s, idx) => {
                                const wrapper = document.createElement('div');
                                wrapper.className = 'sentence-item';
                                const p = document.createElement('p');
                                p.textContent = `${idx+1}. ${s.sentence}`;
                                const meta = document.createElement('div');
                                meta.className = 'sentence-meta';
                                meta.textContent = `Score: ${s.score.toFixed(3)} | Tokens: ${s.tokens.join(' ')}`;
                                wrapper.appendChild(p);
                                wrapper.appendChild(meta);
                                sentencesBody.appendChild(wrapper);
                            });
                        }
                        sentencesModal.setAttribute('aria-hidden', 'false');
                        sentencesModal.style.display = 'block';
                    }

                    function openProcess() {
                        processBody.innerHTML = '';
                        const proc = data.process || {};
                        const ul = document.createElement('ul');
                        ul.className = 'process-list';

                        const addItem = (k, v) => {
                            const li = document.createElement('li');
                            li.innerHTML = `<strong>${k}:</strong> ${typeof v === 'object' ? JSON.stringify(v) : v}`;
                            ul.appendChild(li);
                        };

                        addItem('Method', proc.method || '');
                        addItem('Sentence count', proc.sentence_count || 0);
                        addItem('Selected count', proc.selected_count || 0);
                        addItem('Embedding dim', proc.embedding_dim || 0);
                        addItem('Notes', proc.notes || '');
                        if (proc.scores) addItem('Top scores', proc.scores);

                        processBody.appendChild(ul);
                        // Also show normalized tokens of the selected sentences if present
                        if (data.selected_sentences && data.selected_sentences.length) {
                            const hdr = document.createElement('h5');
                            hdr.textContent = 'Normalized tokens for selected sentences:';
                            processBody.appendChild(hdr);
                            data.selected_sentences.forEach((s, idx) => {
                                const d = document.createElement('div');
                                d.className = 'norm-item';
                                d.innerHTML = `<strong>${idx+1}.</strong> ${s.normalized_tokens.join(' ')}`;
                                processBody.appendChild(d);
                            });
                        }

                        processModal.setAttribute('aria-hidden', 'false');
                        processModal.style.display = 'block';
                    }

                    btn1.addEventListener('click', openSentences);
                    btn2.addEventListener('click', openProcess);

                    // Close buttons
                    document.getElementById('close-sentences').addEventListener('click', () => {
                        document.getElementById('sentences-modal').style.display = 'none';
                    });
                    document.getElementById('close-process').addEventListener('click', () => {
                        document.getElementById('process-modal').style.display = 'none';
                    });
                }
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
