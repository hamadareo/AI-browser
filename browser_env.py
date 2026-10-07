from playwright.sync_api import sync_playwright

class BrowserEnv:
    def __init__(self):
        self.playwright = sync_playwright().start()
        # headless=False enables us to see what the AI is doing, like Claude in Chrome
        self.browser = self.playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context(
            viewport={'width': 1280, 'height': 800}
        )
        self.page = self.context.new_page()
        
    def goto(self, url):
        try:
            self.page.goto(url)
            self.page.wait_for_load_state("domcontentloaded")
            self._inject_cursor_css()
        except Exception as e:
            print(f"Error navigating to {url}: {e}")
            
    def _inject_cursor_css(self):
        # ページ遷移時にカーソルを描画するための初期化
        try:
            self.page.evaluate("""() => {
                if (!document.getElementById('ai-virtual-cursor')) {
                    const cursor = document.createElement('div');
                    cursor.id = 'ai-virtual-cursor';
                    cursor.style.position = 'fixed';
                    cursor.style.width = '24px';
                    cursor.style.height = '24px';
                    cursor.style.borderRadius = '50%';
                    cursor.style.backgroundColor = 'rgba(0, 122, 255, 0.7)';
                    cursor.style.border = '3px solid white';
                    cursor.style.boxShadow = '0 0 10px rgba(0,0,0,0.5)';
                    cursor.style.zIndex = '10000000';
                    cursor.style.pointerEvents = 'none';
                    cursor.style.transition = 'all 0.6s cubic-bezier(0.25, 1, 0.5, 1)'; // 滑らかなアニメーション
                    cursor.style.left = (window.innerWidth / 2) + 'px';
                    cursor.style.top = (window.innerHeight / 2) + 'px';
                    document.body.appendChild(cursor);
                }
            }""")
        except:
            pass
            
    def _move_virtual_mouse(self, element_id):
        # 該当要素の位置を計算し、仮想カーソルを移動させる
        script = f"""(elementId) => {{
            const el = document.querySelector(`[data-ai-id="${{elementId}}"]`);
            if (!el) return false;
            
            const rect = el.getBoundingClientRect();
            const targetX = rect.left + rect.width / 2;
            const targetY = rect.top + rect.height / 2;
            
            const cursor = document.getElementById('ai-virtual-cursor');
            if (cursor) {{
                cursor.style.left = targetX + 'px';
                cursor.style.top = targetY + 'px';
                
                // クリックっぽいアニメーション（一瞬小さくする）
                setTimeout(() => {{
                    cursor.style.transform = 'scale(0.7)';
                    setTimeout(() => {{ cursor.style.transform = 'scale(1)'; }}, 50);
                }}, 100);
            }}
            return true;
        }}"""
        try:
            success = self.page.evaluate(script, element_id)
            if success:
                # アニメーションが終わるまで少し待つ
                self.page.wait_for_timeout(150)
        except:
            pass
            
    def get_state(self):
        # 画面上に以前描画したラベル（ID表示）をクリアする
        self.page.evaluate("""() => {
            document.querySelectorAll('.ai-label').forEach(el => el.remove());
        }""")
        
        # クリック可能な要素を抽出し、赤いラベルを描画して、テキストのリストを返すスクリプト
        script = """() => {
            const maxScroll = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
            const currentScroll = window.scrollY;
            const scrollPercent = maxScroll > 0 ? Math.round((currentScroll / maxScroll) * 100) : 100;
            const scrollInfo = `[Scroll Position: ${scrollPercent}%, Can Scroll Down: ${scrollPercent < 100}]`;
            
            let idCounter = 1;
            // 操作可能な主要な要素を取得
            const interactables = Array.from(document.querySelectorAll('*')).filter(el => {
                const tag = el.tagName.toLowerCase();
                if (['button', 'a', 'input', 'textarea', 'select'].includes(tag)) return true;
                if (el.getAttribute('role') === 'button' || el.getAttribute('tabindex') || el.getAttribute('onclick')) return true;
                const style = window.getComputedStyle(el);
                return style.cursor === 'pointer';
            });
            const elements = [];
            
            interactables.forEach(el => {
                const rect = el.getBoundingClientRect();
                // 画面内に見えている（ある程度幅・高さがある）要素のみ対象とする
                const isVisible = rect.width >= 5 && rect.height >= 5 && 
                                  window.getComputedStyle(el).visibility !== 'hidden' &&
                                  window.getComputedStyle(el).display !== 'none' &&
                                  window.getComputedStyle(el).opacity !== '0';
                
                if (isVisible) {
                    const id = idCounter++;
                    el.setAttribute('data-ai-id', id);
                    
                    // Claude in Chromeのように、画面上に番号ラベルを描画する
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
                    label.style.zIndex = '999999';
                    label.style.pointerEvents = 'none'; // クリックの邪魔にならないようにする
                    label.className = 'ai-label';
                    document.body.appendChild(label);
                    
                    let tag = el.tagName.toLowerCase();
                    if (tag === 'input') {
                        const type = el.type || 'text';
                        if (['submit', 'button', 'reset', 'checkbox', 'radio'].includes(type)) {
                            tag = `button (type="${type}")`;
                        } else {
                            tag = `input_text (type="${type}")`;
                        }
                    } else if (tag === 'textarea') {
                        tag = 'input_text (textarea)';
                    }
                    
                    // 要素のテキストやプレースホルダーを取得
                    let text = el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || el.name || '';
                    text = text.replace(/\\s+/g, ' ').trim().substring(0, 50); // 長すぎるテキストは切り詰める
                    
                    // LLMに渡すための情報リストを生成
                    if (text) {
                        elements.push(`[${id}] ${tag} - "${text}"`);
                    } else {
                        elements.push(`[${id}] ${tag}`);
                    }
                }
            });
            return scrollInfo + '\\n' + elements.join('\\n');
        }"""
        return self.page.evaluate(script)
        
    def click(self, element_id):
        self._move_virtual_mouse(element_id)
        selector = f'[data-ai-id="{element_id}"]'
        try:
            # force=True で多少覆われていてもクリックを試みる
            self.page.click(selector, force=True, timeout=3000)
            self.page.wait_for_load_state("domcontentloaded")
            self._inject_cursor_css() # ページが遷移した可能性があるため再注入
            return None
        except Exception as e:
            return f"Failed to click element {element_id}: {e}"
            
    def type_text(self, element_id, text):
        self._move_virtual_mouse(element_id)
        selector = f'[data-ai-id="{element_id}"]'
        try:
            self.page.fill(selector, text, timeout=3000)
            # 入力後にフォーカスを保持しておく（その後のEnterキーを効かせるため）
            self.page.focus(selector)
            return None
        except Exception as e:
            return f"Failed to type text in element {element_id}: {e}"
            
    def press_enter(self):
        self.page.keyboard.press("Enter")
        self.page.wait_for_load_state("domcontentloaded")
        
    def scroll_down(self):
        self.page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
        self.page.wait_for_timeout(500)
        
    def scroll_up(self):
        self.page.evaluate("window.scrollBy(0, -window.innerHeight * 0.8)")
        self.page.wait_for_timeout(500)
        
    def go_back(self):
        try:
            self.page.go_back(timeout=5000)
            self.page.wait_for_load_state("domcontentloaded")
            self._inject_cursor_css()
        except Exception as e:
            print(f"Error navigating back: {e}")
            
    def close(self):
        self.browser.close()
        self.playwright.stop()
