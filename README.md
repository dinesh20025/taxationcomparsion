# taxationcomparsionaine 4 parts banaye hai. Sab same folder mein rakhna. Aapki 2 files: new_act.txt (2025) aur old_act.txt (1961).

📁 Folder Structure

income_tax_bot/  
├── new_act.txt          ← aapka 2025 extraction  
├── old_act.txt          ← aapka 1961 extraction  
├── 1_parse.py           ← sections todega  
├── 2_chatbot.py         ← search + NVIDIA API  
└── sections.json        ← auto-banega  
STEP 1: 1_parse.py (Text ko Sections mein Todo)

import re  
import json  
  
def parse_act(filepath, act_name):  
    """Ek act file ko sections mein todta hai"""  
    with open(filepath, "r", encoding="utf-8") as f:  
        text = f.read()  
  
    # --- Cleaning: faltu lines hatao ---  
    text = re.sub(r'-+ ?Page \d+ ?-+', '\n', text)  
    text = re.sub(r'Income Tax DepartmentMinistry of Finance, Government of India', '\n', text)  
    text = re.sub(r'Downloaded/Printed on.*?gov\.in', '', text)  
    text = re.sub(r'CHAPTER IV', '\n', text)  
    text = re.sub(r'COMPUTATION OF TOTAL INCOME', '', text)  
  
    # --- Sections split karo ---  
    # Pattern: line start pe number (jaise 13. 14. 14A. 32AB.) + space + Capital letter  
    parts = re.split(r'\n\s*(\d+[A-Z]{0,3})\.\s+(?=[A-Z])', text)  
  
    sections = []  
    # parts[0] = intro junk, phir [num, content, num, content...]  
    for i in range(1, len(parts) - 1, 2):  
        sec_num = parts[i].strip()  
        body = parts[i + 1].strip()  
  
        # Title = pehli line (usually heading), text = baaki  
        lines = body.split('\n', 1)  
        title = lines[0].strip()[:120]      # pehli line title  
        full_text = body  
  
        # Bahut chhote junk skip karo  
        if len(full_text) < 30:  
            continue  
  
        sections.append({  
            "act": act_name,  
            "section": sec_num,  
            "title": title,  
            "text": full_text  
        })  
  
    return sections  
  
  
# --- Dono acts parse karo ---  
all_sections = []  
all_sections += parse_act("new_act.txt", "New Act 2025")  
all_sections += parse_act("old_act.txt", "Old Act 1961")  
  
# Save  
with open("sections.json", "w", encoding="utf-8") as f:  
    json.dump(all_sections, f, indent=2, ensure_ascii=False)  
  
print(f"✅ Total sections parsed: {len(all_sections)}")  
print("✅ Saved to sections.json")  
  
# Sample dikhao  
for s in all_sections[:3]:  
    print(f"\n[{s['act']}] Section {s['section']}: {s['title'][:60]}")  
Chalao: python 1_parse.py
Output dekho — kitne sections bane. sections.json khol ke verify karo.

STEP 2: 2_chatbot.py (Search + NVIDIA API + Chat)

import json  
import re  
from openai import OpenAI  
  
# ============ NVIDIA API SETUP ============  
client = OpenAI(  
    base_url="https://integrate.api.nvidia.com/v1",  
    api_key="nvapi-XXXXXXXXXXXXXXXXX"   # ⚠️ apni key daalo  
)  
MODEL = "nvidia/nemotron-3-ultra-550b-a55b"   # ⚠️ page se exact naam confirm karo  
  
# ============ DATA LOAD ============  
with open("sections.json", "r", encoding="utf-8") as f:  
    SECTIONS = json.load(f)  
  
  
# ============ SEARCH (keyword scoring) ============  
def search(query, top_k=3):  
    """Query se best matching sections dhundta hai (simple TF scoring)"""  
    q_words = set(re.findall(r'\w+', query.lower()))  
    # common words hatao  
    stop = {"the", "a", "is", "of", "in", "what", "how", "kya", "hai", "mein", "ka", "ki", "ke"}  
    q_words -= stop  
  
    scored = []  
    for sec in SECTIONS:  
        text_low = (sec["title"] + " " + sec["text"]).lower()  
        score = 0  
        for w in q_words:  
            score += text_low.count(w)  
        # exact section number match → bada boost  
        if re.search(rf'\b{re.escape(query.strip())}\b', sec["section"], re.I):  
            score += 1000  
        if score > 0:  
            scored.append((score, sec))  
  
    scored.sort(key=lambda x: x[0], reverse=True)  
    return [s for _, s in scored[:top_k]]  
  
  
# ============ ASK NEMOTRON (RAG) ============  
def ask(question):  
    # 1. Relevant sections dhundo  
    hits = search(question, top_k=3)  
  
    if not hits:  
        context = "No matching section found."  
    else:  
        context = ""  
        for h in hits:  
            # context chhota rakho (har section ka pehla part)  
            snippet = h["text"][:2500]  
            context += f"\n--- [{h['act']}] Section {h['section']}: {h['title']} ---\n{snippet}\n"  
  
    # 2. Prompt banao  
    system_prompt = (  
        "You are an Income Tax Act expert assistant. "  
        "Answer ONLY using the provided sections below. "  
        "If answer not in context, say 'Given sections mein ye info nahi mili.' "  
        "Always mention the Section number and which Act (New 2025 / Old 1961). "  
        "Answer in simple language."  
    )  
    user_prompt = f"CONTEXT:\n{context}\n\nQUESTION: {question}"  
  
    # 3. API call (streaming)  
    print("\n🤖 Nemotron: ", end="", flush=True)  
    completion = client.chat.completions.create(  
        model=MODEL,  
        messages=[  
            {"role": "system", "content": system_prompt},  
            {"role": "user", "content": user_prompt}  
        ],  
        temperature=0.2,  
        max_tokens=1000,  
        stream=True  
    )  
    for chunk in completion:  
        if chunk.choices[0].delta.content:  
            print(chunk.choices[0].delta.content, end="", flush=True)  
    print("\n")  
  
    # 4. Sources dikhao  
    if hits:  
        print("📚 Sources:", ", ".join(f"[{h['act']}] Sec {h['section']}" for h in hits))  
  
  
# ============ CHAT LOOP ============  
if __name__ == "__main__":  
    print("=" * 50)  
    print("💼 Income Tax Act Chatbot (New 2025 + Old 1961)")  
    print("Type 'quit' to exit")  
    print("=" * 50)  
  
    while True:  
        q = input("\n❓ Aapka sawaal: ").strip()  
        if q.lower() in ("quit", "exit", "q"):  
            print("Bye! 👋")  
            break  
        if not q:  
            continue  
        try:  
            ask(q)  
        except Exception as e:  
            print(f"\n❌ Error: {e}")  
STEP 3: Chalane ka Tarika

# 1. Library install (sirf ek baar)  
pip install openai  
  
# 2. API key + model name set karo (file ke top mein)  
  
# 3. Sections banao  
python 1_parse.py  
  
# 4. Chatbot chalao  
python 2_chatbot.py  
Try karo ye sawaal:

What is salary under Income Tax?
section 17 perquisite
capital gains kya hai
new act mein standard deduction kitna hai
⚠️ Important Checks
Cheez	Kya karna
Model name	build.nvidia.com pe nemotron page → sample code → exact model="..." copy karo
API key	nvapi-... wali key file mein daalo
Parsing	Agar sections kam bane, toh 1_parse.py ka regex thoda adjust karenge — output batana
🔧 Agar Search Improve Karna Ho (Baad Mein)
Abhi keyword search hai (fast, no extra setup). Baad mein semantic search (meaning samjhe) chahiye toh:


pip install sentence-transformers  
Tab embeddings se search hoga — "income from job" type karo toh "salary" wala section bhi mil jayega. Ye Phase 2 mein add kar denge.

Ab Aap Ye Karo 🎯
1_parse.py chalao → batao kitne sections bane
API key + model name daalo
2_chatbot.py chalao → ek sawaal pucho
Result/error batao
Jo bhi issue aaye (parsing kam, API error), output paste karo — turant fix karenge! 💪

python -c "open('new_act.txt',encoding='utf-8').read().upper().count('CHAPTER')"  

python -c "import re; t=open('new_act.txt',encoding='utf-8').read(); print(re.findall(r'CHAPTER[\s\-]+[IVXLC0-9]+', t, re.I)[:10])"  
