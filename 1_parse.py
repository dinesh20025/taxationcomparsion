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
    parts = re.split(r'(?:^|\n)\s*(\d+[A-Z]{0,3})\.\s+', text)  
  
    sections = []  
    for i in range(1, len(parts) - 1, 2):  
        sec_num = parts[i].strip()  
        body = parts[i + 1].strip()  
        if len(body) < 20:  
            continue  
        title = body.split('\n', 1)[0].strip()[:120]  
        sections.append({  
            "act": act_name,  
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
  
print("=" * 55)  
print(f"✅ Total sections parsed: {len(all_sections)}")  
print("✅ Saved to sections.json")  
print("=" * 55)  
  
if all_sections:  
    print("\n📋 Sample sections (pehle 5):\n")  
    for s in all_sections[:5]:  
        print(f"  [{s['act']}] Sec {s['section']:<5} | len={len(s['text']):<5} | {s['title'][:50]}")
