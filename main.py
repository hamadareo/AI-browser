import time
import os
import difflib
from browser_env import BrowserEnv
from agent import BrowserAgent

def main():
    print("========================================")
    print("🤖 Local AI Browser Agent (Claude in Chrome風)")
    print("========================================")
    print("LM Studioが起動し、Local Server (Port: 1234) がオンになっていることを確認してください。\n")
    
    instruction = input("AIブラウザに依頼する内容を入力してください\n(例: 'Wikipediaで人工知能について検索して'): ")
    
    if not instruction.strip():
        print("指示が入力されなかったため終了します。")
        return

    print("\nブラウザを起動しています...")
    env = BrowserEnv()
    
    # 接続テストも兼ねてAgentを初期化（モデル名はLM Studioでロードされているものが自動で使われるため任意でOK）
    agent = BrowserAgent()
    
    # 初期ページとしてDuckDuckGoを開く（GoogleはBot判定が厳しいため）
    print("DuckDuckGoのトップページに移動します...")
    env.goto("https://duckduckgo.com")
    
    
    # メモリファイルの初期化
    memory_file = "memory.txt"
    memory_text = ""
    if os.path.exists(memory_file):
        with open(memory_file, "r", encoding="utf-8") as f:
            memory_text = f.read()
            if memory_text.strip():
                print(f"🧠 長期記憶（過去の教訓）を {len(memory_text.splitlines())} 件読み込みました。")

    max_steps = 30
    last_error = None
    action_history = []
    
    for step in range(max_steps):
        print(f"\n--- Step {step+1} ---")
        # 描画と安定化のための短いウェイト（速度向上のため短縮）
        time.sleep(0.3)
        
        # 1. 状態の取得
        print("画面の情報を取得中...")
        page_state = env.get_state()
        url = env.page.url
        
        if last_error:
            page_state = f"PREVIOUS ACTION FAILED WITH ERROR:\n{last_error}\n\nDo NOT repeat the exact same action. Try another element or strategy.\n\nPage Elements:\n{page_state}"
            last_error = None
            
        if action_history:
            # 最新の直近5アクション程度を履歴として渡す（長すぎるとコンテキストを圧迫するため）
            history_str = "\\n".join([f"Step {i+1}: {act}" for i, act in enumerate(action_history[-5:])])
            page_state = f"--- PREVIOUS ACTIONS HISTORY ---\\n{history_str}\\n\\nReview your history. DO NOT repeat the exact same action endlessly. If you just used TYPE to enter text into a search box, your next action MUST be ENTER or CLICKing a search button.\\n\\n--- CURRENT PAGE ELEMENTS ---\\n{page_state}"
        

        # 2. LLMに推論させる
        print("AIが次のアクションを考えています...")
        action_str_raw = agent.get_next_action(instruction, url, page_state, memory_text=memory_text)
        
        try:
            import json, re
            # Extract JSON block in case there's markdown or extra text
            match = re.search(r'\{.*\}', action_str_raw, re.DOTALL)
            if match:
                action_data = json.loads(match.group(0))
            else:
                action_data = json.loads(action_str_raw)
                
            print(f"🧐 [評価]: {action_data.get('evaluation', '')}")
            
            # 新しい教訓があれば保存
            new_lesson = action_data.get('lessons_learned', '').strip()
            if new_lesson:
                is_duplicate = False
                for existing_lesson in memory_text.splitlines():
                    existing_lesson = existing_lesson.replace("- ", "").strip()
                    if not existing_lesson: continue
                    similarity = difflib.SequenceMatcher(None, new_lesson, existing_lesson).ratio()
                    if similarity > 0.8:
                        is_duplicate = True
                        break
                        
                if not is_duplicate:
                    print(f"🎓 [新しく学んだこと]: {new_lesson}")
                    with open(memory_file, "a", encoding="utf-8") as f:
                        f.write(f"- {new_lesson}\\n")
                    memory_text += f"- {new_lesson}\\n"
                else:
                    print(f"🎓 [重複のため記録スキップ]: {new_lesson}")
                
            mem_ref = action_data.get('memory_reflection', '').strip()
            if mem_ref:
                print(f"🧠 [記憶からの気付き]: {mem_ref}")
            print(f"💡 [思考]: {action_data.get('thought', '')}")
            
            # ブラウザ画面上にAIの思考を表示するHUD
            mem_html = f'<div style="color:#88ccff; font-size: 0.85em; margin-bottom: 8px;">🧠 記憶: {mem_ref.replace("'", "\\'").replace('"', '\\"').replace("\\n", " ")}</div>' if mem_ref else ''
            thought_text = action_data.get('thought', '').replace("'", "\\'").replace('"', '\\"').replace('\\n', ' ')
            eval_text = action_data.get('evaluation', '').replace("'", "\\'").replace('"', '\\"').replace('\\n', ' ')
            lesson_html = f'<br><br><span style="color:#ffd700; font-size: 0.85em;">🎓 新しい学び:<br>{new_lesson.replace("'", "\\'").replace('"', '\\"').replace("\\n", " ")}</span>' if new_lesson else ''
            
            hud_script = f"""() => {{
                let hud = document.getElementById('ai-hud');
                if (!hud) {{
                    hud = document.createElement('div');
                    hud.id = 'ai-hud';
                    hud.style.position = 'fixed';
                    hud.style.bottom = '20px';
                    hud.style.left = '20px';
                    hud.style.backgroundColor = 'rgba(0, 0, 0, 0.85)';
                    hud.style.color = 'white';
                    hud.style.padding = '15px';
                    hud.style.borderRadius = '10px';
                    hud.style.zIndex = '10000001';
                    hud.style.fontFamily = 'sans-serif';
                    hud.style.maxWidth = '400px';
                    hud.style.boxShadow = '0 4px 20px rgba(0,0,0,0.5)';
                    hud.style.pointerEvents = 'none';
                    hud.style.lineHeight = '1.4';
                    document.body.appendChild(hud);
                }}
                hud.innerHTML = `{mem_html}<strong>🤖 AIの思考:</strong><br>{thought_text}<br><br><span style="color:#aaa; font-size: 0.85em;">🧐 自己評価:<br>{eval_text}</span>{lesson_html}`;
            }}"""
            try:
                env.page.evaluate(hud_script)
            except:
                pass
            
            action_type = action_data.get('action_type')
            element_id = action_data.get('element_id')
            text = action_data.get('text')
            
            # format for history
            action_str = str(action_type)
            if element_id is not None: action_str += f" {element_id}"
            if text: action_str += f" '{text}'"
            print(f"▶️ [実行]: {action_str}")
            
        except Exception as e:
            print(f"JSONパースエラー: {e}\\nLLM出力: {action_str_raw}")
            last_error = f"Failed to parse your response as JSON. Make sure you output ONLY valid JSON. Error: {e}"
            continue

        action_history.append(action_str)
        
        # 3. アクションの実行
        try:
            if action_type == "GOTO":
                env.goto(text)
            elif action_type == "CLICK":
                err = env.click(element_id)
                if err:
                    print(f"⚠️ {err}")
                    last_error = err
            elif action_type == "TYPE":
                err = env.type_text(element_id, text)
                if err:
                    print(f"⚠️ {err}")
                    last_error = err
            elif action_type == "ENTER":
                env.press_enter()
            elif action_type == "SCROLL_DOWN":
                env.scroll_down()
            elif action_type == "SCROLL_UP":
                env.scroll_up()
            elif action_type == "GO_BACK":
                env.go_back()
            elif action_type == "DONE":
                print(f"✅ タスク完了！ {text}")
                break
            else:
                print(f"⚠️ 不明なアクション: {action_type}")
                last_error = f"Unknown action_type: {action_type}"
        except Exception as e:
            print(f"❌ アクションの実行中にエラーが発生しました: {e}")
            last_error = str(e)
            
    print("\\n終了します。10秒後にブラウザを閉じます（結果を確認してください）。")
    time.sleep(10)
    env.close()

if __name__ == "__main__":
    main()
