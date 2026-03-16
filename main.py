import os
import warnings

# --- שלב 1: "ניתוח לב פתוח" לספריות התקשורת (חובה לפני כל השאר!) ---
try:
    import httpx
    # אנחנו מחליפים את פונקציית הבדיקה של httpx כך שתמיד תחזיר "מאושר"
    orig_init = httpx.Client.__init__
    def unverified_init(self, *args, **kwargs):
        kwargs['verify'] = False
        orig_init(self, *args, **kwargs)
    httpx.Client.__init__ = unverified_init
    
    # אותו דבר לגרסה האסינכרונית (למקרה הצורך)
    orig_async_init = httpx.AsyncClient.__init__
    def unverified_async_init(self, *args, **kwargs):
        kwargs['verify'] = False
        orig_async_init(self, *args, **kwargs)
    httpx.AsyncClient.__init__ = unverified_async_init
except ImportError:
    pass

# ביטול אזהרות SSL בטרמינל
warnings.filterwarnings('ignore')
os.environ['CURL_CA_BUNDLE'] = ""
os.environ['REQUESTS_CA_BUNDLE'] = ""
os.environ['PYTHONHTTPSVERIFY'] = "0"
# -------------------------------------------------------------------

from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings, StorageContext
from llama_index.llms.cohere import Cohere
from llama_index.embeddings.cohere import CohereEmbedding
from llama_index.vector_stores.pinecone import PineconeVectorStore
from pinecone import Pinecone

# 1. טעינת מפתחות
load_dotenv()
cohere_key = os.getenv("COHERE_API_KEY")
pinecone_key = os.getenv("PINECONE_API_KEY")

print("מגדירים את המודל (Cohere)...")
Settings.llm = Cohere(api_key=cohere_key, model="command-r-08-2024") 
Settings.embed_model = CohereEmbedding(api_key=cohere_key, model_name="embed-multilingual-v3.0")

print("קוראים מסמכים...")
try:
    cursor_documents = SimpleDirectoryReader("cursor_docs").load_data()
    claude_documents = SimpleDirectoryReader("claude_code_docs").load_data()
    all_documents = cursor_documents + claude_documents
    print(f"נטענו {len(all_documents)} מסמכים.")
except Exception as e:
    print(f"שגיאה בקריאת הקבצים: {e}")
    all_documents = []

if all_documents:
    print("מתחברים ל-Pinecone...")
    pc = Pinecone(api_key=pinecone_key)
    pinecone_index = pc.Index("rag-project")
    vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    print("מתרגמים ושומרים (זה השלב הקריטי)...")
    index = VectorStoreIndex.from_documents(
        all_documents, 
        storage_context=storage_context
    )
    print("הכל עבר בהצלחה! 🎉 המידע בתוך המחסן!")
else:
    print("עצירה: לא נמצאו קבצים בתיקיות.")