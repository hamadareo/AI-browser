from openai import OpenAI

class BrowserAgent:
    def __init__(self, base_url="http://localhost:1234/v1", model_name="local-model"):
        # LM Studio等のローカルOpenAI互換サーバーに接続
        self.client = OpenAI(base_url=base_url, api_key="lm-studio")
        self.model = model_name
        
    def get_next_action(self, instruction, url, page_state, memory_text=""):
        memory_section = f"\\n--- LONG-TERM MEMORY (過去の教訓) ---\\n{memory_text}\\nKeep these lessons in mind to avoid repeating past mistakes.\\n-----------------------------------------------------\\n" if memory_text.strip() else ""
        
        system_prompt = f"""You are an autonomous web browser agent.
Your goal is to complete the user's instruction.
You MUST respond with a valid JSON object ONLY. Do not use markdown like ```json.
The JSON must exactly match this structure:
{{
  "memory_reflection": "(日本語で記述) LONG-TERM MEMORYの中に現在の状況に使える教訓はあるか？あれば今回の行動にどう活かすか考えてください",
  "evaluation": "(日本語で記述) 前回の自分の操作が成功したか評価し、エラーやループがあれば原因と対策を考えてください",
  "lessons_learned": "(日本語で記述) 今回の操作から得た新しい教訓を「もし[条件]なら[行動]する」という具体的なルール形式で書いてください。特になければ空文字にしてください",
  "thought": "(日本語で記述) 目標達成のために次に何をするべきか、どの要素を操作するかを考えてください",
  "action_type": "GOTO" | "CLICK" | "TYPE" | "ENTER" | "SCROLL_DOWN" | "SCROLL_UP" | "GO_BACK" | "DONE",
  "element_id": 123,
  "text": "text to type or url"
}}
{memory_section}
RULES:
- `memory_reflection`, `evaluation`, `lessons_learned`, and `thought` MUST be written in Japanese.
- If action_type is "CLICK", element_id is REQUIRED (integer).
- If action_type is "TYPE", element_id (integer) and text (string) are REQUIRED.
- If action_type is "GOTO", text (string URL) is REQUIRED.
- For ENTER, SCROLL_DOWN, SCROLL_UP, GO_BACK, DONE, set element_id and text to null.
- If you typed text into a search box in the previous step, your action_type MUST be "ENTER" or "CLICK" the search button now. Do NOT TYPE again.
- If the element you are looking for is NOT in the current page elements, and you can scroll down, you MUST use "SCROLL_DOWN" to search for it autonomously.
- If you are stuck on a page, got an error that you can't bypass, or need to return to the previous page, you MUST use "GO_BACK".
- Do NOT output "DONE" until you have visually confirmed on the screen that the user's goal has been fully achieved (e.g., search results are displayed).
"""
        
        user_prompt = f"""
Instruction: {instruction}
Current URL: {url}

{page_state}

Respond ONLY with the JSON object.
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3, # 推論の柔軟性を高めるために0.1から0.3に増加
                max_tokens=1500 # 思考が途切れないよう十分に確保
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM Error: {e}")
            print("LM Studioが起動しているか、ローカルサーバー(ポート1234)がオンになっているか確認してください。")
            return "ERROR"
