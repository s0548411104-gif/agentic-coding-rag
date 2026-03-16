import os
import ssl
import urllib3
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

# ביטול אזהרות האבטחה של נטפרי
urllib3.disable_warnings()
ssl._create_default_https_context = ssl._create_unverified_context

# טוענים את המפתח שלנו
load_dotenv()
pinecone_key = os.getenv("PINECONE_API_KEY")

print("מתחברים ל-Pinecone...")
pc = Pinecone(api_key=pinecone_key)

index_name = "rag-project"

# בודקים אם המחסן כבר קיים, ואם לא - יוצרים אותו
if index_name not in pc.list_indexes().names():
    print(f"יוצר את המחסן '{index_name}' (זה יכול לקחת דקה-שתיים, נא להמתין)...")
    pc.create_index(
        name=index_name,
        dimension=1024,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )
    print("המחסן נוצר בהצלחה! 🎉")
else:
    print("המחסן כבר קיים ומוכן לעבודה!")