import re  
import json  
  
def clean_text(text):  
    """Faltu headers/footers hatao"""  
    text = re.sub(r'-+ ?Page \d+ ?-+', '\n', text)  
    text = re.sub(r'Income Tax Department\s*Ministry of Finance.*?India', '\n', text, flags=re.I)  
    text = re.sub(r'Downloaded/Printed on.*?gov\.in', '', text, flags=re.I)  
    text = re.sub(r'Ministry of Finance, Government of India', '\n', text, flags=re.I)  
    text = re.sub(r'[ \t]+', ' ', text)          # multiple spaces -> single  
    return text  
  
  
def parse_act(filepath, act_name):  
    """Ek act file ko sections mein todta hai"""  
    try:  
        with open(filepath, "r", encoding="utf-8") as f:  
            text = f.read()  
    except FileNotFoundError:  
        print(f"⚠️  File nahi mili: {filepath} (skip kar raha hoon)")  
        return []  
  
    text = clean_text(text)  
  
    # Pattern: section number line start pe. Examples: "17.", "32AB.", "14A."  
    # Splits text wherever a new section number appears  
    parts = re.split(r'(?:^|\n)\s*(\d+[A-Z]{0,3})\.\s+', text)  
  
    sections = []  
    # parts[0] = junk before first section, phir [num, body, num, body...]  
    for i in range(1, len(parts) - 1, 2):  
        sec_num = parts[i].strip()  
        body = parts[i + 1].strip()  
  
        if len(body) < 20:      # bahut chhota = junk  
            continue  
  
        # Title = pehli line ya pehle 100 char tak  
        first_line = body.split('\n', 1)[0].strip()  
        title = first_line[:120]  
  
        sections.append({  
            "act": act_name,  
            "section": sec_num,  
            "title": title,  
            "text": body  
        })  
  
    return sections  
  
  
# ===== Dono acts parse karo =====  
all_sections = []  
all_sections += parse_act("new_act.txt", "New Act 2025")  
all_sections += parse_act("old_act.txt", "Old Act 1961")  
  
# Save  
with open("sections.json", "w", encoding="utf-8") as f:  
    json.dump(all_sections, f, indent=2, ensure_ascii=False)  
  
# ===== Report =====  
print("=" * 55)  
print(f"✅ Total sections parsed: {len(all_sections)}")  
print("✅ Saved to sections.json")  
print("=" * 55)  
  
if all_sections:  
    print("\n📋 Sample sections (pehle 5):\n")  
    for s in all_sections[:5]:  
        print(f"  [{s['act']}] Sec {s['section']:<5} | "  
              f"len={len(s['text']):<5} | {s['title'][:55]}")  
else:  
    print("\n❌ KOI section nahi bana! Text format alag hoga.")  
    print("   new_act.txt ka top 30 lines bhejo, regex adjust karenge.") 
