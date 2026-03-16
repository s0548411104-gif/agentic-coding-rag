# 📊 RAG Agentic Coding Docs - Project

פרויקט זה בונה מערכת **RAG (Retrieval-Augmented Generation)** חכמה המאפשרת למתכנתים לתשאל את מסמכי התיעוד של כלי קידוד אוטונומיים (כמו Cursor ו-Claude Code). 

המערכת סורקת קבצי `md`, מאנדקסת אותם ומאפשרת לשאול שאלות על החלטות עיצוב, חוקי קוד ומפרטים טכניים שנשמרו לאורך תהליך הפיתוח.

## 🛠️ טכנולוגיות בשימוש
* **LlamaIndex:** Framework לניהול שכבת הידע וה-RAG.
* **Cohere:** שימוש במודלי Embedding לתרגום סמנטי של הטקסט.
* **Pinecone:** מסד נתונים וקטורי לשמירה ושליפה מהירה של המידע.
* **Gradio:** ממשק משתמש אינטראקטיבי לצ'אט.

## 📂 מבנה התיקיות שנסרקו
המערכת מאגדת ידע מהכלים הבאים:
1. **Cursor:** תיעוד מתוך תיקיית `cursor_docs` (קבצי `spec.md`).
2. **Claude Code:** תיעוד מתוך תיקיית `claude_code_docs` (קבצי `rules.md`).

## 🚀 איך להריץ את הפרויקט?

1. **התקנת ספריות:**
    ```bash
    pip install llama-index llama-index-llms-cohere llama-index-embeddings-cohere llama-index-vector-stores-pinecone gradio python-dotenv python-certifi-win32

2. הגדרת מפתחות: יש ליצור קובץ .env ולהזין את המפתחות של COHERE_API_KEY ו-PINECONE_API_KEY

3. טעינת נתונים: הרצת הקובץ שסורק את המסמכים ומעלה אותם ל-Pinecone:
python main.py

4. הפעלת הצ'אט: הרצת ממשק המשתמש:
python chat.py

🙋 דוגמאות לשאלות שהמערכת יודעת לענות עליהן
"מה הצבע העיקרי שנבחר לדיזיין של המערכת?"

"אילו חוקי קוד הוגדרו עבור כתיבת פונקציות?"

"באילו שפות פיתוח נעשה שימוש בפרויקט?" 