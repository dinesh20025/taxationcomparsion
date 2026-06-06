import json  
import re  
from openai import OpenAI  
  
# ============ API SETUP ============  
client = OpenAI(  
    base_url="https://integrate.api.nvidia.com/v1",  
    api_key="nvapi-XXXXXXXXXXXXXXXXX"          # ⚠️ apni key daalo  
)  
MODEL = "mistralai/mistral-medium-3.5-128b"  
  
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
        "give","details","detail","meaning","information","info","do",  
        "can","i","claim","get","my","your","changes","change","new",  
        "old","act","compare","comparison","difference","vs","between",  
        "naye","naya","purane","purana","badlaav","antar","farak","chapter",  
        "batao","baare","bare","kuch","bhi","puche","pucho"}  
  
ROMAN = {'i':'1','ii':'2','iii':'3','iv':'4','v':'5','vi':'6','vii':'7',  
         'viii':'8','ix':'9','x':'10','xi':'11','xii':'12','xiii':'13',  
         'xiv':'14','xv':'15','xvi':'16','xvii':'17','xviii':'18',  
         'xix':'19','xx':'20'}  
  
  
# ============ QUERY ANALYSIS ============  
def detect_chapter(query):  
    """Query mein chapter number hai? (Chapter 4, Chapter IV, chapter 4)"""  
    m = re.search(r'chapter[\s\-]+([ivxlc]+|\d+)', query, re.IGNORECASE)  
    if not m:  
        return None  
    raw = m.group(1).lower()  
    return ROMAN.get(raw, raw)  
  
  
def is_comparison(query):  
    keys = ["compare","comparison","difference","vs","versus","change",  
            "changes","badlaav","antar","farak","old and new","new and old",  
            "purane","naye","dono act"]  
    q = query.lower()  
    return any(k in q for k in keys)  
  
  
def get_chapter_sections(chap_num, act_filter=None):  
    out = []  
    for s in SECTIONS:  
        if s.get("chapter") == chap_num:  
            if act_filter is None or act_filter in s["act"]:  
                out.append(s)  
    return out  
  
  
def get_section(sec_num):  
    sec_num = sec_num.upper()  
    return [s for s in SECTIONS if s["section"].upper() == sec_num]  
  
  
# ============ SMART SEARCH ============  
def smart_search(query):  
    # 1. Chapter query?  
    chap = detect_chapter(query)  
    if chap:  
        hits = get_chapter_sections(chap)  
        if hits:  
            return hits, "chapter", chap  
  
    # 2. Section numbers?  
    nums = re.findall(r'\b(\d+[A-Za-z]{0,4})\b', query)  
    nums = [n.upper() for n in nums if not n.isdigit() or len(n) <= 4]  
    hits = []  
    for n in nums:  
        hits.extend(get_section(n))  
  
    # 3. Keyword fallback  
    if not hits:  
        q_words = set(re.findall(r'\w+', query.lower())) - STOP  
        scored = []  
        for sec in SECTIONS:  
            text_low = (sec["title"] + " " + sec["text"]).lower()  
            title_low = sec["title"].lower()  
            score = sum(text_low.count(w) + title_low.count(w) * 3  
                        for w in q_words)  
            if score > 0:  
                scored.append((score, sec))  
        scored.sort(key=lambda x: x[0], reverse=True)  
        hits = [s for _, s in scored[:5]]  
  
    # Dedupe  
    seen, unique = set(), []  
    for h in hits:  
        k = (h["act"], h["section"])  
        if k not in seen:  
            seen.add(k)  
            unique.append(h)  
    return unique[:8], "normal", None  
  
  
# ============ ASK (Claude-style) ============  
def ask(question):  
    hits, mode, chap = smart_search(question)  
    compare = is_comparison(question)  
  
    if not hits:  
        print("\n⚠️  Kuch match nahi hua.")  
        return  
  
    # Context banao (chapter mode mein chhota text, zyada sections)  
    per_sec = 800 if mode == "chapter" else 2000  
    context = ""  
    for h in hits:  
        ct = f" (Chapter {h.get('chapter','?')})" if h.get('chapter') else ""  
        context += (f"\n=== [{h['act']}]{ct} Section {h['section']}: "  
                    f"{h['title']} ===\n{h['text'][:per_sec]}\n")  
  
    if mode == "chapter":  
        print(f"\n📖 Chapter {chap} ki {len(hits)} sections mili")  
    print("🔎 Found:", ", ".join(  
        f"[{h['act'].split()[0]}] Sec {h['section']}" for h in hits[:8]))  
  
    # ---- SYSTEM PROMPT (Claude Opus style) ----  
    base_persona = (  
        "You are a brilliant, friendly Indian Income Tax expert — like a "  
        "top consultant who explains things clearly and thoroughly. "  
        "Use ONLY the provided context. Never make up info. "  
        "If something isn't in the context, honestly say so. "  
        "Write in clear Hinglish. Use headings, bullet points, and tables "  
        "where helpful. Be thorough but not verbose. "  
        "Always cite Section numbers and which Act (New 2025 / Old 1961)."  
    )  
  
    if mode == "chapter":  
        task = (  
            f"The user is asking about CHAPTER {chap}. Give a complete, "  
            "well-organized overview:\n"  
            "1. **Chapter ka overview** — ye chapter kis baare mein hai (2-3 lines)\n"  
            "2. **Important sections** — har key section ko 1-2 line mein samjhao\n"  
            "3. **Key takeaways** — sabse zaroori points bullet mein\n"  
            "Make it scannable and easy to understand."  
        )  
    elif compare:  
        task = (  
            "The user wants a COMPARISON between Old Act (1961) and New "  
            "Act (2025). Structure:\n"  
            "1. **Purpose** — section kis liye hai (1 line)\n"  
            "2. **Old Act 1961** — kya tha\n"  
            "3. **New Act 2025** — kya hai\n"  
            "4. **Key Changes** — kya badla (bullets)\n"  
            "5. **Comparison Table** — Old vs New\n"  
            "Agar section sirf ek act mein hai to clearly batao."  
        )  
    else:  
        task = (  
            "Answer the question clearly and completely. Start with a direct "  
            "answer, then explain with details, examples if relevant, and "  
            "structure it nicely with headings/bullets."  
        )  
  
    system_prompt = base_persona + "\n\nTASK:\n" + task  
    user_prompt = f"CONTEXT:\n{context}\n\nQUESTION: {question}"  
  
    try:  
        completion = client.chat.completions.create(  
            model=MODEL,  
            messages=[  
                {"role": "system", "content": system_prompt},  
                {"role": "user", "content": user_prompt}  
            ],  
            temperature=0.4,  
            top_p=1.0,  
            max_tokens=2500,  
            stream=True  
        )  
  
        printed = False  
        for chunk in completion:  
            if not chunk.choices:  
                continue  
            d = chunk.choices[0].delta  
            if d.content:  
                if not printed:  
                    print("\n🤖 Answer:\n", end="", flush=True)  
                    printed = True  
                print(d.content, end="", flush=True)  
        print("\n")  
  
    except Exception as e:  
        print(f"\n❌ API Error: {e}")  
        return  
  
    print("📚 Sources:", ", ".join(  
        f"[{h['act']}] Sec {h['section']}" for h in hits[:8]))  
  
  
# ============ CHAT LOOP ============  
if __name__ == "__main__":  
    print("=" * 60)  
    print("💼 Income Tax AI — Chapter + Section + Compare 🧠")  
    print("   New Act 2025  vs  Old Act 1961")  
    print("   Examples:")  
    print("     • chapter 4 ke baare mein batao")  
    print("     • 80C aur 80CCD ke naye act mein changes")  
    print("     • section 17 explain karo")  
    print("   Type 'quit' to exit")  
    print("=" * 60)  
  
    while True:  
        q = input("\n❓ Sawaal: ").strip()  
        if q.lower() in ("quit", "exit", "q"):  
            print("Bye! 👋")  
            break  
        if not q:  
            continue  
        ask(q)
