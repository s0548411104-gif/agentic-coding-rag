import os
import ssl
import warnings
import asyncio
import json
import gradio as gr
from dotenv import load_dotenv

# --- מעקף SSL לנטפרי (חובה לכל קובץ שעובד מול הרשת) ---
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
# ----------------------------------------------------

from llama_index.core.workflow import (
    Event, 
    StartEvent, 
    StopEvent, 
    Workflow, 
    step
)
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.llms import ChatMessage # הוספנו את זה בשביל התיקון של תחנה 3
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.embeddings.cohere import CohereEmbedding
from llama_index.llms.cohere import Cohere
from pinecone import Pinecone

# 1. טעינת הגדרות ומפתחות
load_dotenv()
cohere_key = os.getenv("COHERE_API_KEY")
pinecone_key = os.getenv("PINECONE_API_KEY")

# 2. הגדרת המודלים (כולל תיקון הזיכרון כדי שלא יקרוס)
Settings.llm = Cohere(api_key=cohere_key, model="command-r-08-2024")
Settings.context_window = 4096
# הגדלתי מעט את ה-num_output כדי לאפשר רשימות ארוכות אם ישלפו מה-JSON
Settings.num_output = 512 
Settings.embed_model = CohereEmbedding(api_key=cohere_key, model_name="embed-multilingual-v3.0")

# ==========================================
# שלב ב' + ג': ארכיטקטורת Event-Driven Workflow + נתב
# ==========================================

# אלו ה"אירועים" (Events) שעוברים בין התחנות
class ValidationEvent(Event):
    """אירוע שמשוגר אם השאלה עברה ולידציה"""
    query: str

class RetrievalEvent(Event):
    """אירוע שמשוגר אחרי שהמידע הרלוונטי נשלף"""
    context: str
    query: str

class RAGWorkflow(Workflow):
    
    @step
    async def validate_query(self, ev: StartEvent) -> ValidationEvent | StopEvent:
        """
        תחנה 1: בדיקות ולידציה.
        דרישת מטלה: "בדיקות תקינות פשוטות שמונעות 'שטויות': קלט ריק..."
        """
        user_query = ev.query
        
        # ולידציה: האם הקלט ריק או קצר מדי?
        if not user_query or len(user_query.strip()) < 3:
            return StopEvent(result="השאלה קצרה מדי או ריקה. אנא נסי שוב.")
        
        print(f"[Workflow] תחנה 1: השאלה '{user_query}' עברה ולידציה.")
        # משגרים אירוע לתחנה הבאה
        return ValidationEvent(query=user_query)

    @step
    async def route_and_retrieve(self, ev: ValidationEvent) -> RetrievalEvent | StopEvent:
        """
        תחנה 2: נתב (Router) ואחזור מידע.
        בודק אם השאלה מבקשת רשימה/חוקים וניגש ל-JSON, אחרת ניגש ל-Pinecone.
        """
        user_query = ev.query
        keywords_for_structured = ["רשימה", "חוקים", "החלטות", "כל ה"]
        
        # --- ניתוב לשליפה מובנית (JSON - שלב ג') ---
        if any(word in user_query for word in keywords_for_structured):
            print("[Workflow] תחנה 2: הנתב זיהה בקשה לרשימה -> קורא מקובץ ה-JSON!")
            try:
                with open("output.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                context = json.dumps(data, ensure_ascii=False, indent=2)
                return RetrievalEvent(context=f"זהו מידע מובנה שחולץ לקובץ JSON:\n{context}", query=user_query)
            except Exception as e:
                return StopEvent(result=f"שגיאה בקריאת הנתונים המובנים: {e}")
        
        # --- ניתוב לחיפוש סמנטי (Pinecone - שלבים א'+ב') ---
        print("[Workflow] תחנה 2: הנתב בחר בחיפוש סמנטי ב-Pinecone...")
        pc = Pinecone(api_key=pinecone_key)
        pinecone_index = pc.Index("rag-project")
        vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
        
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        # שולפים רק את התוצאה הכי טובה כדי לחסוך מקום
        retriever = index.as_retriever(similarity_top_k=1) 
        
        nodes = retriever.retrieve(ev.query)
        context = "\n".join([n.get_content() for n in nodes])
        
        # ולידציה: האם בכלל נמצא מידע?
        if not context:
             return StopEvent(result="מצטער, לא מצאתי מידע רלוונטי בקבצי התיעוד לטובת השאלה הזו.")
             
        print(f"[Workflow] תחנה 2: נמצא מידע. עובר לניסוח תשובה.")
        # משגרים אירוע לתחנה הסופית
        return RetrievalEvent(context=context, query=ev.query)

    @step
    async def generate_response(self, ev: RetrievalEvent) -> StopEvent:
        """
        תחנה 3: סינתוז תשובה בעזרת ה-LLM.
        """
        print("[Workflow] תחנה 3: מנסח תשובה מול מודל השפה...")
        
        # התיקון: פרומפט (הנחיה) הרבה יותר נוקשה למודל שמונע "הזיות" ושטויות, ותומך ב-JSON
        prompt = (
            f"המידע מהמערכת:\n{ev.context}\n\n"
            f"השאלה של המשתמש: {ev.query}\n\n"
            f"הנחיה למערכת: עליך לענות על השאלה בצורה ברורה *אך ורק* על סמך 'המידע מהמערכת' המצורף. "
            f"אם המידע מצורף בפורמט JSON, עליך לקרוא אותו ולנסח ממנו תשובה קריאה וברורה בשפה טבעית (למשל רשימה ממוספרת). "
            f"אם השאלה היא מילת נימוס (כמו 'שלום'), מילות סתם (כמו 'אאא'), או שהתשובה לא נמצאת במידע - "
            f"אסור לך בשום אופן להמציא תשובה או לסכם את המידע סתם. במקרה כזה עליך לענות בדיוק במילים אלו: "
            f"'מצטער, לא מצאתי מידע רלוונטי לשאלה שלך בקבצי התיעוד של הפרויקט'."
        )
        
        # עוטפים את השאלה כאובייקט צ'אט
        messages = [ChatMessage(role="user", content=prompt)]
        response = Settings.llm.chat(messages)
        
        print("[Workflow] תהליך הסתיים בהצלחה.")
        return StopEvent(result=str(response))

# ==========================================
# ממשק המשתמש (Gradio)
# ==========================================

# פונקציית מעטפת כדי ש-Gradio ידע לעבוד עם ה-Workflow האסינכרוני
async def chat_wrapper(message, history):
    wf = RAGWorkflow(timeout=30)
    try:
        # הפעלת ה-Workflow בצורה טבעית
        result = await wf.run(query=message)
        return str(result)
    except Exception as e:
        return f"קרתה תקלה במהלך ה-Workflow: {e}"

demo = gr.ChatInterface(
    fn=chat_wrapper,
    title="צ'אטבוט מושלם 🎓 (כולל שלב ג')",
    description="מערכת RAG המשלבת Workflow (שלב ב') ונתב חכם למידע מובנה או סמנטי (שלב ג').",
    examples=["מהם הצבעים המרכזיים?", "תן לי רשימה של כל החוקים וההחלטות", "x"]
)

if __name__ == "__main__":
    from llama_index.utils.workflow import draw_all_possible_flows
    my_workflow = RAGWorkflow(timeout=30)
    draw_all_possible_flows(my_workflow, filename="workflow.html")
    demo.launch()