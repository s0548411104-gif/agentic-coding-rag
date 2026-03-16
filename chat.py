import os
import ssl
import warnings
import gradio as gr
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, Settings
from llama_index.llms.cohere import Cohere
from llama_index.embeddings.cohere import CohereEmbedding
from llama_index.vector_stores.pinecone import PineconeVectorStore
from pinecone import Pinecone

# --- מעקף SSL לנטפרי ---
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
# ------------------------------

load_dotenv()
cohere_key = os.getenv("COHERE_API_KEY")
pinecone_key = os.getenv("PINECONE_API_KEY")

# הגדרת המודל עם הגבלת זיכרון כדי למנוע את השגיאה שקיבלת
Settings.llm = Cohere(api_key=cohere_key, model="command-r-08-2024")
Settings.context_window = 4096 # הגדרת גודל החלון של המודל
Settings.num_output = 256
Settings.embed_model = CohereEmbedding(api_key=cohere_key, model_name="embed-multilingual-v3.0")

# חיבור למחסן
pc = Pinecone(api_key=pinecone_key)
pinecone_index = pc.Index("rag-project")
vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

# יצירת מנוע חיפוש "רזה" יותר (similarity_top_k=2) כדי שלא יחרוג מהזיכרון
query_engine = index.as_query_engine(similarity_top_k=2)


# --- שלב ג': פונקציית הנתב (Router) ---
def router_logic(user_message):
    """
    הנתב מחליט האם ללכת לחיפוש סמנטי (Pinecone) 
    או להחזיר תשובה מובנית (JSON)
    """
    keywords_for_structured = ["רשימה", "כל החוקים", "החלטות", "טבלה", "JSON"]
    
    # אם המשתמש מבקש רשימה או מידע מבני
    if any(word in user_message for word in keywords_for_structured):
        print("--- הנתב בחר: שליפה מובנית (Structured) ---")
        return "נראה שביקשת רשימה מובנית. (כאן המערכת תשלוף מתוך קובץ ה-output.json שייצרנו בשלב ג')."
    
    # אחרת - חיפוש סמנטי רגיל
    print("--- הנתב בחר: חיפוש סמנטי (Pinecone) ---")
    response = query_engine.query(user_message)
    return str(response)

def chat_with_bot(user_message, history):
    try:
        # הפעלת הנתב
        result = router_logic(user_message)
        return result
    except Exception as e:
        return f"שגיאה: {e}"

demo = gr.ChatInterface(
    fn=chat_with_bot,
    title="הצ'אטבוט החכם - גרסה סופית 🎓",
    description="מערכת RAG הכוללת חיפוש סמנטי ונתב (Router) לפי דרישות הפרויקט.",
    examples=["מהם הצבעים המרכזיים?", "תן לי רשימה של כל החוקים"]
)

if __name__ == "__main__":
    demo.launch()