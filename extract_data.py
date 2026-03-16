import os
import ssl
import warnings
import json
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader
from llama_index.llms.cohere import Cohere
from llama_index.core.program import LLMTextCompletionProgram
from pydantic import BaseModel, Field
from typing import List

# --- מעקף SSL לנטפרי (כדי שיוכל להתחבר ל-API) ---
warnings.filterwarnings('ignore')
os.environ['PYTHONHTTPSVERIFY'] = "0"
os.environ['CURL_CA_BUNDLE'] = ""
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError: pass
else: ssl._create_default_https_context = _create_unverified_https_context
try:
    import httpx
    orig_init = httpx.Client.__init__
    def unverified_init(self, *args, **kwargs):
        kwargs['verify'] = False
        orig_init(self, *args, **kwargs)
    httpx.Client.__init__ = unverified_init
except ImportError: pass
# ------------------------------------------------

# 1. הגדרת המבנה שאנחנו רוצים לחלץ (Pydantic Models)
class Decision(BaseModel):
    title: str = Field(description="כותרת ההחלטה")
    summary: str = Field(description="סיכום קצר של ההחלטה")

class Rule(BaseModel):
    rule: str = Field(description="הכלל או ההנחיה")
    scope: str = Field(description="התחום אליו הכלל שייך (עיצוב/קוד/DB)")

class ExtractionResult(BaseModel):
    decisions: List[Decision]
    rules: List[Rule]

# 2. פונקציה לביצוע החילוץ
def extract_structured_data():
    load_dotenv()
    # תיקון שם המודל לגרסה שעדיין עובדת בשרתים
    llm = Cohere(api_key=os.getenv("COHERE_API_KEY"), model="command-r-08-2024")
    
    # קריאת המסמכים
    cursor_docs = SimpleDirectoryReader(input_dir="./cursor_docs").load_data()
    claude_docs = SimpleDirectoryReader(input_dir="./claude_code_docs").load_data()
    all_documents = cursor_docs + claude_docs
    
    # איחוד כל הטקסט למשתנה אחד כדי שה-AI יוכל לעבור עליו
    all_text = "\n".join([d.text for d in all_documents])

    # הגדרת ה"תוכנית" לחילוץ
    prompt_template_str = (
        "אתה מומחה לניתוח מערכות. עבור על הטקסט הבא וחלץ ממנו את כל ההחלטות והחוקים "
        "לפי המבנה המבוקש. טקסט:\n{desktop_text}"
    )
    
    program = LLMTextCompletionProgram.from_defaults(
        output_cls=ExtractionResult,
        prompt_template_str=prompt_template_str,
        llm=llm
    )

    # הרצה אמיתית של החילוץ (הורדנו את ההערות)
    print("מתחיל חילוץ נתונים מול ה-API... (זה עשוי לקחת כחצי דקה)")
    try:
        result = program(desktop_text=all_text)
        result_dict = result.dict()
        
        # שמירת התוצאה לקובץ JSON
        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=4)
            
        print("הנתונים חולצו בהצלחה ונשמרו לקובץ 'output.json'!")
        return result_dict
    except Exception as e:
        print(f"שגיאה בתהליך: {e}")

if __name__ == "__main__":
    extract_data = extract_structured_data()