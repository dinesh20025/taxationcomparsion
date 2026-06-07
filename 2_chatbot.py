import json  
import re  
from openai import OpenAI  
  
# ============ API SETUP ============  
client = OpenAI(  
    base_url="https://integrate.api.nvidia.com/v1",  
    api_key="nvapi-XXXXXXXXXXXXXXXXX"          # ⚠️ apni key daalo  
)  
MODEL = "mistralai/mistral-small-4-119b-2603"  
  
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
  
def is_opinion(query):  
    """User opinion/recommendation maang raha hai?"""  
    keys = ["which is better","kaunsa sahi","kaunsa better","kaunsa achha",  
            "kaun sa","should i","recommend","suggest","best","behtar",  
            "sahi hai","advice","advise","opinion","prefer","better",  
            "konsa","beneficial","faydemand","kya choose","choose karu"]  
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
        hits = [s for _, s in scored[:3]]  
  
    # Dedupe  
    seen, unique = set(), []  
    for h in hits:  
        k = (h["act"], h["section"])  
        if k not in seen:  
            seen.add(k)  
            unique.append(h)  
    return unique[:6], "normal", None  
  
# ============ ASK (Claude-style) ============  
def ask(question):  
    hits, mode, chap = smart_search(question)  
    compare = is_comparison(question)  
    opinion = is_opinion(question)  
  
    # ⚡ Agar exact match nahi mila, fir bhi jawab do (general mode)  
    no_context = False  
    if not hits:  
        no_context = True  
        print("\n💡 Direct match nahi mila — general guidance de raha hu...")  
        q_words = set(re.findall(r'\w+', question.lower())) - STOP  
        scored = []  
        for sec in SECTIONS:  
            text_low = (sec["title"] + " " + sec["text"]).lower()  
            score = sum(text_low.count(w) for w in q_words)  
            if score > 0:  
                scored.append((score, sec))  
        scored.sort(key=lambda x: x[0], reverse=True)  
        hits = [s for _, s in scored[:3]]      # jo bhi mile, top 3  
  
    # ⚡ Context build (chhota = fast)  
    if mode == "chapter":  
        per_sec = 600  
    else:  
        per_sec = 1200  
  
    context = ""  
    for h in hits:  
        ct = f" (Chapter {h.get('chapter','?')})" if h.get('chapter') else ""  
        context += (f"\n=== [{h['act']}]{ct} Section {h['section']}: "  
                    f"{h['title']} ===\n{h['text'][:per_sec]}\n")  
  
    if not context.strip():  
        context = "(No specific section found in the database for this query.)"  
  
    if mode == "chapter":  
        print(f"\n📖 Chapter {chap} mein {len(hits)} sections mili")  
    if hits:  
        print("🔎 Found:", ", ".join(  
            f"[{h['act'].split()[0]}] Sec {h['section']}" for h in hits[:6]))  
  
    # ---- SYSTEM PROMPT (English output, opinion allowed) ----  
    base_persona = (  
        "You are a brilliant, friendly Indian Income Tax expert — like a "  
        "top consultant who explains things clearly and thoroughly. "  
        "Base your facts on the provided context. Never invent specific "  
        "numbers, section text, or rules that aren't supported. "  
        "HOWEVER, you ARE allowed and encouraged to give your professional "  
        "OPINION, ANALYSIS, and RECOMMENDATIONS by reasoning over the "  
        "context — e.g. which Act is more beneficial, pros and cons, what a "  
        "taxpayer should consider. Clearly label these as analysis "  
        "('In my view…', 'Recommendation:'). "  
        "If the context truly lacks the info needed, give general guidance "  
        "but clearly note it. Never refuse to answer. "  
        "ALWAYS respond in clear, professional ENGLISH (never Hinglish). "  
        "Use headings, bullet points, and tables where helpful. "  
        "Be thorough but not verbose. "  
        "Always cite Section numbers and which Act (New 2025 / Old 1961)."  
    )  
  
    if mode == "chapter":  
        task = (  
            f"The user is asking about CHAPTER {chap}. Give a complete, "  
            "well-organized overview in English:\n"  
            "1. **Chapter Overview** — what this chapter covers (2-3 lines)\n"  
            "2. **Important Sections** — explain each key section in 1-2 lines\n"  
            "3. **Key Takeaways** — the most important points as bullets\n"  
            "Make it scannable and easy to understand."  
        )  
        max_tok = 1800  
    elif opinion:  
        task = (  
            "The user is asking for your PROFESSIONAL OPINION / "  
            "RECOMMENDATION (e.g. which Act or option is better). "  
            "Respond in English with this structure:\n"  
            "1. **Quick Answer** — your clear recommendation in 1-2 lines "  
            "(don't dodge the question)\n"  
            "2. **Reasoning** — explain WHY, based on the context (pros/cons "  
            "of each option)\n"  
            "3. **Comparison Table** — if comparing options/Acts\n"  
            "4. **My Recommendation** — clearly state what you'd advise and "  
            "for WHOM it suits (e.g. 'New Act suits taxpayers who…')\n"  
            "5. **Note** — mention it depends on individual circumstances.\n"  
            "Be decisive and give a real opinion — don't just list facts."  
        )  
        max_tok = 1800  
    elif compare:  
        task = (  
            "The user wants a COMPARISON between the Old Act (1961) and the "  
            "New Act (2025). Respond in English with this structure:\n"  
            "1. **Purpose** — what the section is for (1 line)\n"  
            "2. **Old Act 1961** — what it stated\n"  
            "3. **New Act 2025** — what it states now\n"  
            "4. **Key Changes** — what changed (bullets)\n"  
            "5. **Comparison Table** — Old vs New\n"  
            "6. **Which is More Beneficial** — give your brief opinion\n"  
            "If the section exists in only one Act, clearly mention that."  
        )  
        max_tok = 1800  
    else:  
        if no_context:  
            task = (  
                "No exact matching section was found in the database. Do your "  
                "best to answer helpfully in English using any relevant "  
                "context provided. If the context is not directly relevant, "  
                "give general guidance about Indian Income Tax, but clearly "  
                "mention: 'Note: This is general guidance — please verify "  
                "with the specific Act section.' Always be helpful and never "  
                "refuse to answer."  
            )  
            max_tok = 1000  
        else:  
            task = (  
                "Answer the question clearly and completely in English. Start "  
                "with a direct answer, then explain with details, examples if "  
                "relevant, and structure it nicely with headings/bullets. "  
                "If the user seems to want guidance, feel free to add a brief "  
                "professional recommendation at the end."  
            )  
            max_tok = 1000  
  
    system_prompt = base_persona + "\n\nTASK:\n" + task  
    user_prompt = f"CONTEXT:\n{context}\n\nQUESTION: {question}\n\n(Respond in English only.)"  
  
    try:  
        completion = client.chat.completions.create(  
            model=MODEL,  
            messages=[  
                {"role": "system", "content": system_prompt},  
                {"role": "user", "content": user_prompt}  
            ],  
            temperature=0.3,  
            top_p=1.0,  
            max_tokens=max_tok,  
            stream=True,  
            extra_body={"reasoning_effort": "low"}   # ⚡ FAST (high mat karo)  
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
  
    if hits:  
        print("📚 Sources:", ", ".join(  
            f"[{h['act']}] Sec {h['section']}" for h in hits[:6]))  
  
# ============ CHAT LOOP ============  
if __name__ == "__main__":  
    print("=" * 60)  
    print("💼 Income Tax AI — Chapter + Section + Compare + Opinion 🧠")  
    print("   New Act 2025  vs  Old Act 1961")  
    print("   Examples:")  
    print("     • chapter 4 ke baare mein batao")  
    print("     • 80C aur 80CCD ke naye act mein changes")  
    print("     • new aur old act mein kaunsa better hai?")  
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
