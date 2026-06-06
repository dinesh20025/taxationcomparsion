import re  
import json  
  
def clean_text(text):  
    text = re.sub(r'-+ ?Page \d+ ?-+', '\n', text)  
    text = re.sub(r'Income Tax Department\s*Ministry of Finance.*?India', '\n', text, flags=re.I)  
    text = re.sub(r'Downloaded/Printed on.*?gov\.in', '', text, flags=re.I)  
    text = re.sub(r'[ \t]+', ' ', text)  
    return text  
  
  
def parse_act(filepath, act_name):  
    try:  
        with open(filepath, "r", encoding="utf-8") as f:  
            text = f.read()  
    except FileNotFoundError:  
        print(f"⚠️  File nahi mili: {filepath} (skip)")  
        return []  
  
    text = clean_text(text)  
  
    # ---- CHAPTER markers dhundo ----  
    # "CHAPTER IV", "CHAPTER 4", "Chapter IV - Computation" etc.  
    chapter_pattern = re.compile(  
        r'CHAPTER[\s\-]+([IVXLC]+|\d+)[\s\-:.]*([A-Z][A-Za-z ,&\-]{0,80})?',  
        re.IGNORECASE  
    )  
  
    # Roman to number map (1-30 kaafi hai)  
    roman = {'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7,'VIII':8,  
             'IX':9,'X':10,'XI':11,'XII':12,'XIII':13,'XIV':14,'XV':15,  
             'XVI':16,'XVII':17,'XVIII':18,'XIX':19,'XX':20,'XXI':21,  
             'XXII':22,'XXIII':23,'XXIV':24,'XXV':25}  
  
    def chap_num(raw):  
        raw = raw.upper().strip()  
        if raw.isdigit():  
            return raw  
        return str(roman.get(raw, raw))  
  
    # Chapters ke positions nikaalo  
    chapters = []  
    for m in chapter_pattern.finditer(text):  
        chapters.append({  
            "pos": m.start(),  
            "num": chap_num(m.group(1)),  
            "title": (m.group(2) or "").strip().title()  
        })  
  
    def find_chapter(pos):  
        current = {"num": "?", "title": ""}  
        for c in chapters:  
            if c["pos"] <= pos:  
                current = c  
            else:  
                break  
        return current  
  
    # ---- SECTIONS nikaalo ----  
    sections = []  
    sec_pattern = re.compile(r'(?:^|\n)\s*(\d+[A-Z]{0,3})\.\s+')  
  
    matches = list(sec_pattern.finditer(text))  
    for idx, m in enumerate(matches):  
        sec_num = m.group(1).strip()  
        start = m.end()  
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)  
        body = text[start:end].strip()  
  
        if len(body) < 20:  
            continue  
  
        chap = find_chapter(m.start())  
        title = body.split('\n', 1)[0].strip()[:120]  
  
        sections.append({  
            "act": act_name,  
            "chapter": chap["num"],  
            "chapter_title": chap["title"],  
            "section": sec_num,  
            "title": title,  
            "text": body  
        })  
    return sections  
  
  
all_sections = []  
all_sections += parse_act("new_act.txt", "New Act 2025")  
all_sections += parse_act("old_act.txt", "Old Act 1961")  
  
with open("sections.json", "w", encoding="utf-8") as f:  
    json.dump(all_sections, f, indent=2, ensure_ascii=False)  
  
print("=" * 60)  
print(f"✅ Total sections parsed: {len(all_sections)}")  
print("✅ Saved to sections.json")  
print("=" * 60)  
  
# Chapter summary dikhao  
if all_sections:  
    print("\n📚 Chapters detected:\n")  
    seen = {}  
    for s in all_sections:  
        key = (s["act"], s["chapter"])  
        if key not in seen:  
            seen[key] = s["chapter_title"]  
    for (act, ch), title in sorted(seen.items()):  
        print(f"  [{act}] Chapter {ch:<4} | {title[:45]}")  
  
    print("\n📋 Sample sections:\n")  
    for s in all_sections[:5]:  
        print(f"  [{s['act']}] Ch{s['chapter']:<3} Sec {s['section']:<5} | {s['title'][:40]}")
