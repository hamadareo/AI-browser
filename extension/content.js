function injectLabels() {
    // Clear old labels
    document.querySelectorAll('.ai-label').forEach(el => el.remove());
    
    let idCounter = 1;
    const elements = [];
    
    const interactables = Array.from(document.querySelectorAll('*')).filter(el => {
        const tag = el.tagName.toLowerCase();
        if (['button', 'a', 'input', 'textarea', 'select'].includes(tag)) return true;
        if (el.getAttribute('role') === 'button' || el.getAttribute('tabindex') || el.onclick) return true;
        const style = window.getComputedStyle(el);
        return style.cursor === 'pointer';
    });
    
    interactables.forEach(el => {
        const rect = el.getBoundingClientRect();
        const isVisible = rect.width >= 5 && rect.height >= 5 && 
                          window.getComputedStyle(el).visibility !== 'hidden' &&
                          window.getComputedStyle(el).display !== 'none' &&
                          window.getComputedStyle(el).opacity !== '0';
        
        if (isVisible) {
            const id = idCounter++;
            el.setAttribute('data-ai-id', id);
            
            const label = document.createElement('div');
            label.textContent = id;
            label.style.position = 'absolute';
            label.style.left = (rect.left + window.scrollX) + 'px';
            label.style.top = (rect.top + window.scrollY) + 'px';
            label.style.backgroundColor = 'rgba(255, 0, 0, 0.8)';
            label.style.color = 'white';
            label.style.fontSize = '12px';
            label.style.fontWeight = 'bold';
            label.style.padding = '1px 4px';
            label.style.borderRadius = '3px';
            label.style.zIndex = '2147483647'; // max z-index
            label.style.pointerEvents = 'none';
            label.className = 'ai-label';
            document.body.appendChild(label);
            
            let tag = el.tagName.toLowerCase();
            if (tag === 'input') {
                tag = `input (type="${el.type || 'text'}")`;
            }
            
            let text = el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || el.name || '';
            text = text.replace(/\s+/g, ' ').trim().substring(0, 50);
            
            elements.push(`[${id}] ${tag} ${text ? '- "' + text + '"' : ''}`);
        }
    });
    
    const scrollInfo = `[Scroll Position: ${Math.round((window.scrollY / Math.max(1, document.documentElement.scrollHeight - window.innerHeight)) * 100)}%]`;
    return scrollInfo + '\n' + elements.join('\n');
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "GET_STATE") {
        const state = injectLabels();
        sendResponse({ state: state });
        return true;
    }
    
    if (request.action === "EXECUTE_ACTION") {
        const data = request.data;
        const type = data.action_type;
        
        try {
            if (type === "GOTO") {
                window.location.href = data.text;
            } else if (type === "SCROLL_DOWN") {
                window.scrollBy({ top: window.innerHeight * 0.8, behavior: 'smooth' });
            } else if (type === "SCROLL_UP") {
                window.scrollBy({ top: -window.innerHeight * 0.8, behavior: 'smooth' });
            } else if (type === "GO_BACK") {
                window.history.back();
            } else {
                const el = document.querySelector(`[data-ai-id="${data.element_id}"]`);
                if (!el) {
                    sendResponse({ error: "Element not found" });
                    return true;
                }
                
                if (type === "CLICK") {
                    el.click();
                } else if (type === "TYPE") {
                    el.value = data.text;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.focus();
                } else if (type === "ENTER") {
                    const events = ['keydown', 'keypress', 'keyup'];
                    events.forEach(evType => {
                        const ev = new KeyboardEvent(evType, { 
                            key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true 
                        });
                        el.dispatchEvent(ev);
                    });
                    
                    // Fallback for old forms if event didn't trigger navigation
                    if (el.form) {
                        setTimeout(() => {
                            if (!window.location.href.includes('search')) { // heuristic to avoid double submit
                                // el.form.submit(); // Actually, modern SPAs break if you call form.submit(). Relying on events is better.
                            }
                        }, 500);
                    }
                }
            }
            sendResponse({ success: true });
        } catch (e) {
            sendResponse({ error: e.message });
        }
        return true;
    }
});
