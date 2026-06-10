import json  
import re  
import os  
from openai import OpenAI  
  
client = OpenAI(  
    base_url="https://integrate.api.nvidia.com/v1",  
    api_key=os.environ.get("NVIDIA_API_KEY", "nvapi-XXXXX")  # ⚠️ env var  
)  
MODEL = "meta/llama-3.1-8b-instruct"  
  
with open("sections.json", "r", encoding="utf-8") as f:  
    SECTIONS = json.load(f)  
print(f"✅ Loaded {len(SECTIONS)} sections")  
  
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
  
  
def detect_chapter(query):  
    m = re.search(r'chapter[\s\-]+([ivxlc]+|\d+)', query, re.IGNORECASE)  
    if not m:  
        return None  
    raw = m.group(1).lower()  
    return ROMAN.get(raw, raw)  
  
  
def is_comparison(query):  
    keys = ["compare","comparison","difference","vs","versus","change",  
            "changes","badlaav","antar","farak","old and new","new and old",  
            "purane","naye","dono act"]  
    return any(k in query.lower() for k in keys)  
  
  
def is_opinion(query):  
    keys = ["which is better","kaunsa sahi","kaunsa better","kaunsa achha",  
            "kaun sa","should i","recommend","suggest","best","behtar",  
            "sahi hai","advice","advise","opinion","prefer","better",  
            "konsa","beneficial","faydemand","kya choose","choose karu"]  
    return any(k in query.lower() for k in keys)  
  
  
def get_chapter_sections(chap_num):  
    return [s for s in SECTIONS if s.get("chapter") == chap_num]  
  
  
def get_section(sec_num):  
    sec_num = sec_num.upper()  
    return [s for s in SECTIONS if s["section"].upper() == sec_num]  
  
  
def smart_search(query):  
    chap = detect_chapter(query)  
    if chap:  
        hits = get_chapter_sections(chap)  
        if hits:  
            return hits, "chapter", chap  
  
    nums = re.findall(r'\b(\d+[A-Za-z]{0,4})\b', query)  
    nums = [n.upper() for n in nums if not n.isdigit() or len(n) <= 4]  
    hits = []  
    for n in nums:  
        hits.extend(get_section(n))  
  
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
  
    seen, unique = set(), []  
    for h in hits:  
        k = (h["act"], h["section"])  
        if k not in seen:  
            seen.add(k)  
            unique.append(h)  
    return unique[:6], "normal", None  
  
  
def build_prompts(question):  
    hits, mode, chap = smart_search(question)  
    compare = is_comparison(question)  
    opinion = is_opinion(question)  
  
    no_context = False  
    if not hits:  
        no_context = True  
        q_words = set(re.findall(r'\w+', question.lower())) - STOP  
        scored = []  
        for sec in SECTIONS:  
            text_low = (sec["title"] + " " + sec["text"]).lower()  
            score = sum(text_low.count(w) for w in q_words)  
            if score > 0:  
                scored.append((score, sec))  
        scored.sort(key=lambda x: x[0], reverse=True)  
        hits = [s for _, s in scored[:3]]  
  
    per_sec = 600 if mode == "chapter" else 1000     # 1200 -> 1000 (thoda lean)  
    context = ""  
    for h in hits:  
        ct = f" (Chapter {h.get('chapter','?')})" if h.get('chapter') else ""  
        context += (f"\n=== [{h['act']}]{ct} Section {h['section']}: "  
                    f"{h['title']} ===\n{h['text'][:per_sec]}\n")  
    if not context.strip():  
        context = "(No specific section found in the database.)"  
  
    base_persona = (  
        "You are a brilliant, friendly Indian Income Tax expert — like a "  
        "top consultant who explains things clearly. Base facts on the "  
        "provided context. Never invent specific numbers. You ARE allowed "  
        "to give professional OPINION and RECOMMENDATIONS by reasoning over "  
        "the context. Never refuse to answer. ALWAYS respond in clear, "  
        "professional ENGLISH (never Hinglish). Use headings, bullets, and "  
        "tables. Always cite Section numbers and Act (New 2025 / Old 1961)."  
        "\n\nIMPORTANT — VISUAL SUMMARY TABLE:\n"  
        "AFTER your normal text answer, ALWAYS add ONE clean summary table "  
        "wrapped in special tags exactly like this:\n"  
        "[[TAXTABLE: <short title here>]]\n"  
        "| Column1 | Column2 | Column3 |\n"  
        "|---------|---------|---------|\n"  
        "| data | data | data |\n"  
        "[[/TAXTABLE]]\n"  
        "For comparisons use columns: Aspect | Old Act 1961 | New Act 2025. "  
        "For a single section use columns: Particulars | Details. "  
        "Keep it concise (4-7 rows). This table is a VISUAL HIGHLIGHT "  
        "summarising the key points. Never skip this table."  
    )  
  
    if mode == "chapter":  
        task = (f"User asks about CHAPTER {chap}. Give overview:\n"  
                "1. **Chapter Overview**\n2. **Important Sections** (1-2 lines each)\n"  
                "3. **Key Takeaways** (bullets). Make it scannable.")  
        max_tok = 1200                               # 1800 -> 1200  
    elif opinion:  
        task = ("User wants your PROFESSIONAL OPINION/RECOMMENDATION:\n"  
                "1. **Quick Answer** (clear recommendation)\n2. **Reasoning** (pros/cons)\n"  
                "3. **Comparison Table**\n4. **My Recommendation** (for whom)\n"  
                "5. **Note** (depends on circumstances). Be decisive.")  
        max_tok = 1200                               # 1800 -> 1200  
    elif compare:  
        task = ("User wants COMPARISON Old(1961) vs New(2025):\n"  
                "1. **Purpose**\n2. **Old Act 1961**\n3. **New Act 2025**\n"  
                "4. **Key Changes**\n5. **Comparison Table**\n"  
                "6. **Which is More Beneficial** (your opinion).")  
        max_tok = 1300                               # 1800 -> 1300  
    else:  
        if no_context:  
            task = ("No exact section found. Answer helpfully using any "  
                    "context. If not relevant, give general Indian Income "  
                    "Tax guidance but note: 'This is general guidance — "  
                    "verify with the specific Act section.' Never refuse.")  
        else:  
            task = ("Answer clearly in English. Direct answer first, then "  
                    "details with headings/bullets. Add brief recommendation "  
                    "if user wants guidance.")  
        max_tok = 900                                # 1200 -> 900  
  
    system_prompt = base_persona + "\n\nTASK:\n" + task  
    user_prompt = (f"CONTEXT:\n{context}\n\nQUESTION: {question}\n\n"  
                   "(Respond in English only. Remember to add the "  
                   "[[TAXTABLE]] visual summary at the end.)")  
    sources = [f"[{h['act']}] Sec {h['section']}" for h in hits[:6]]  
    return system_prompt, user_prompt, max_tok, sources  
  
  
def ask_stream(question):  
    """Generator — har chunk yield karta hai (streaming ke liye)"""  
    system_prompt, user_prompt, max_tok, sources = build_prompts(question)  
    try:  
        completion = client.chat.completions.create(  
            model=MODEL,  
            messages=[  
                {"role": "system", "content": system_prompt},  
                {"role": "user", "content": user_prompt}  
            ],  
            temperature=0.3,  
            top_p=0.95,  
            max_tokens=max_tok,                              # 800-1300 (lean)  
            stream=True,  
            extra_body={  
                "chat_template_kwargs": {  
                    "thinking": False,                       # 🔑 OFF = tez  
                    "reasoning_effort": "none"               # 🔑 none = tez  
                }  
            }  
        )  
        for chunk in completion:  
            if not chunk.choices:  
                continue  
            d = chunk.choices[0].delta  
            if d.content:  
                yield d.content  
    except Exception as e:  
        yield f"\n\n❌ Error: {e}"
