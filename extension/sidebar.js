const chatContainer = document.getElementById('chat-container');
const taskInput = document.getElementById('task-input');
const sendButton = document.getElementById('send-button');

let isProcessing = false;
let currentTask = "";
let actionHistory = []; // 履歴を保持

async function callLMStudio(prompt) {
    try {
        const response = await fetch('http://localhost:1234/v1/chat/completions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: "local-model",
                messages: [{ role: "user", content: prompt }],
                temperature: 0.3,
                max_tokens: 1500
            })
        });
        const data = await response.json();
        return data.choices[0].message.content.trim();
    } catch (err) {
        console.error("LM Studio error:", err);
        throw new Error("ローカルAI(LM Studio)への接続に失敗しました。起動しているか確認してください。");
    }
}

function appendMessage(role, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}-message`;
    msgDiv.textContent = text;
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return msgDiv;
}

function appendThought(text, evalText = "") {
    const boxDiv = document.createElement('div');
    boxDiv.className = 'thought-box';
    let html = `<strong>🤔 思考:</strong><br>${text}`;
    if (evalText) html += `<br><br><strong>🧐 自己評価:</strong><br>${evalText}`;
    boxDiv.innerHTML = html;
    chatContainer.appendChild(boxDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function showLoading() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'loading-indicator';
    msgDiv.id = 'loading';
    msgDiv.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function removeLoading() {
    const loading = document.getElementById('loading');
    if (loading) loading.remove();
}

async function getPageState() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    return new Promise((resolve) => {
        chrome.tabs.sendMessage(tab.id, { action: "GET_STATE" }, (response) => {
            resolve(response ? response.state : "No state (Refresh the page)");
        });
    });
}

async function executeActionOnPage(actionData) {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    return new Promise((resolve) => {
        chrome.tabs.sendMessage(tab.id, { action: "EXECUTE_ACTION", data: actionData }, (response) => {
            resolve(response);
        });
    });
}

const systemPromptBase = `You are an autonomous web browser agent. Your goal is to complete the user's instruction.
You MUST respond with a valid JSON object ONLY. Do not use markdown like \`\`\`json.
The JSON must exactly match this structure:
{
  "evaluation": "(日本語で記述) 前回の自分の操作が成功したか評価し、エラーやループがあれば原因と対策を考えてください",
  "thought": "(日本語で記述) 目標達成のために次に何をするべきか、どの要素を操作するかを考えてください",
  "action_type": "GOTO" | "CLICK" | "TYPE" | "ENTER" | "SCROLL_DOWN" | "SCROLL_UP" | "GO_BACK" | "DONE",
  "element_id": 123,
  "text": "text to type or url"
}

RULES:
- \`evaluation\` and \`thought\` MUST be written in Japanese.
- If action_type is "CLICK", element_id is REQUIRED (integer).
- If action_type is "TYPE", element_id (integer) and text (string) are REQUIRED.
- If action_type is "GOTO", text (string URL) is REQUIRED.
- For ENTER, SCROLL_DOWN, SCROLL_UP, GO_BACK, DONE, set element_id and text to null.
- If you are stuck, try SCROLL_DOWN or GO_BACK.
- Output "DONE" only when the goal is achieved.
- CRITICAL: If you just used TYPE to enter text into a search box, your next action MUST be ENTER or CLICKing a search button. Do NOT repeat TYPE endlessly.
`;

async function step() {
    if (!isProcessing) return;
    showLoading();
    let state = await getPageState();
    
    let historyStr = "";
    if (actionHistory.length > 0) {
        historyStr = "\\n\\n--- PREVIOUS ACTIONS HISTORY ---\\n" + actionHistory.slice(-5).map((a, i) => `Step ${i+1}: ${a}`).join("\\n") + "\\nReview your history. DO NOT repeat the exact same action. If you typed text, press ENTER next.";
    }

    const prompt = `${systemPromptBase}\n\nInstruction: ${currentTask}${historyStr}\n\n--- CURRENT PAGE ELEMENTS ---\n${state}`;
    
    try {
        const rawJson = await callLMStudio(prompt);
        removeLoading();
        
        let actionData;
        try {
            const match = rawJson.match(/\{[\s\S]*\}/);
            actionData = JSON.parse(match ? match[0] : rawJson);
        } catch (e) {
            appendMessage('system', 'JSONのパースに失敗しました。再試行します。');
            setTimeout(step, 1000);
            return;
        }

        if (actionData.thought) {
            appendThought(actionData.thought, actionData.evaluation);
        }

        let actionStr = actionData.action_type;
        if (actionData.element_id !== null && actionData.element_id !== undefined) actionStr += ` id=${actionData.element_id}`;
        if (actionData.text) actionStr += ` text="${actionData.text}"`;
        actionHistory.push(actionStr);

        if (actionData.action_type === "DONE") {
            appendMessage('system', '✅ タスクが完了しました！');
            isProcessing = false;
            sendButton.disabled = false;
            actionHistory = [];
            return;
        }

        await executeActionOnPage(actionData);
        
        // Wait 2 seconds for page to settle, then next step
        setTimeout(() => {
            if (isProcessing) step();
        }, 2000);

    } catch (err) {
        removeLoading();
        appendMessage('system', err.message);
        isProcessing = false;
        sendButton.disabled = false;
        actionHistory = [];
    }
}

sendButton.addEventListener('click', () => {
    const text = taskInput.value.trim();
    if (!text || isProcessing) return;
    
    currentTask = text;
    taskInput.value = '';
    appendMessage('user', text);
    
    isProcessing = true;
    sendButton.disabled = true;
    actionHistory = [];
    step();
});

taskInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendButton.click();
    }
});
