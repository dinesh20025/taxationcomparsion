import json  
import re  
from openai import OpenAI  
  
# ============ NVIDIA API SETUP ============  
client = OpenAI(  
    base_url="https://integrate.api.nvidia.com/v1",  
    api_key="nvapi-XXXXXXXXXXXXXXXXX"          # ⚠️ apni key daalo  
)  
MODEL = "nvidia/nemotron-3-ultra-550b-a55b"  
SHOW_THINKING = False  
  
# ============ DATA LOAD ============  
try:  
    with open("sections.json", "r", encoding="utf-8") as f:  
        SECTIONS = json.load(f)  
    print(f"✅ Loaded {len(SECTIONS)} sections")  
except FileNotFoundError:  
    print("❌ sections.json nahi mili! Pehle 'python 1_parse.py' chalao.")  
    exit()  
  
STOP = {"the","a","an","is","are","of","in","on","for","to","what","how",  
        "kya","hai","hain","mein","ka","ki","ke","under","define","explain",  
        "and","or","tell","me","about","please","section","sec","s",  
        "give","details","detail","meaning","information","info"}  
  
  
# ============ SEARCH ============  
def search(query, top_k=3):  
    q_words = set(re.findall(r'\w+', query.lower())) - STOP  
  
    # Section number mention? jaise "section 17"  
    num_match = re.search(r'\b(\d+[A-Za-z]{0,3})\b', query)  
    target_num = num_match.group(1).upper() if num_match else None  
    # number ko keyword list se hatao (warna har jagah match karega)  
    if target_num:  
        q_words.discard(target_num.lower())  
  
    scored = []  
    for sec in SECTIONS:  
        text_low = (sec["title"] + " " + sec["text"]).lower()  
        title_low = sec["title"].lower()  
  
        score = 0  
        for w in q_words:  
            score += text_low.count(w)  
            score += title_low.count(w) * 3      # title match zyada important  
  
        # Exact section number -> bada boost  
        if target_num and sec["section"].upper() == target_num:  
            score += 10000  
  
        if score > 0:  
            scored.append((score, sec))  
  
    scored.sort(key=lambda x: x[0], reverse=True)  
    return [s for _, s in scored[:top_k]]  
  
  
# ============ ASK NEMOTRON ============  
def ask(question):  
    hits = search(question, top_k=3)  
  
    if not hits:  
        print("\n⚠️  Koi section match nahi hua.")  
        context = "No matching section found."  
    else:  
        context = ""  
        for h in hits:  
            context += (f"\n--- [{h['act']}] Section {h['section']}: "  
                        f"{h['title']} ---\n{h['text'][:2500]}\n")  
        print("\n🔎 Found:", ", ".join(  
            f"[{h['act']}] Sec {h['section']}" for h in hits))  
  
    system_prompt = (  
        "You are an Income Tax Act expert assistant. "  
        "Answer ONLY using the provided sections below. "  
        "If the answer is not in the context, say 'Given sections mein ye info nahi mili.' "  
        "Always mention the Section number and which Act (New 2025 / Old 1961). "  
        "Answer in simple, clear language."  
    )  
    user_prompt = f"CONTEXT:\n{context}\n\nQUESTION: {question}"  
  
    try:  
        completion = client.chat.completions.create(  
            model=MODEL,  
            messages=[  
                {"role": "system", "content": system_prompt},  
                {"role": "user", "content": user_prompt}  
            ],  
            temperature=0.2,  
            top_p=0.95,  
            max_tokens=8192,  
            extra_body={  
                "chat_template_kwargs": {"enable_thinking": True},  
                "reasoning_budget": 4096  
            },  
            stream=True  
        )  
  
        printed_think = False  
        printed_ans = False  
  
        for chunk in completion:  
            if not chunk.choices:  
                continue  
            delta = chunk.choices[0].delta  
  
            reasoning = getattr(delta, "reasoning_content", None)  
            if reasoning and SHOW_THINKING:  
                if not printed_think:  
                    print("\n💭 Soch raha hai:\n", end="", flush=True)  
                    printed_think = True  
                print(reasoning, end="", flush=True)  
  
            if delta.content:  
                if not printed_ans:  
                    print("\n\n🤖 Nemotron: ", end="", flush=True)  
                    printed_ans = True  
                print(delta.content, end="", flush=True)  
  
        print("\n")  
  
    except Exception as e:  
        print(f"\n❌ API Error: {e}")  
        return  
  
    if hits:  
        print("📚 Sources:", ", ".join(  
            f"[{h['act']}] Sec {h['section']}" for h in hits))  
  
  
# ============ CHAT LOOP ============  
if __name__ == "__main__":  
    print("=" * 55)  
    print("💼 Income Tax Act Chatbot (New 2025 + Old 1961)")  
    print("Type 'quit' to exit")  
    print("=" * 55)  
  
    while True:  
        q = input("\n❓ Aapka sawaal: ").strip()  
        if q.lower() in ("quit", "exit", "q"):  
            print("Bye! 👋")  
            break  
        if not q:  
            continue  
        ask(q)
