# app/rag_qa.py
"""
RAG QA using LangChain + Groq with monitoring and security.
Function: answer(question, top_k=5, model_name="mixtral-8x7b")
Requires: 
- GROQ_API_KEY environment variable
- LANGCHAIN_API_KEY for tracing
"""
import os
from langchain_groq.chat_models import ChatGroq
from langchain.schema import SystemMessage, HumanMessage
from app.rag import retrieve
from dotenv import load_dotenv

os.environ["LANGCHAIN_TRACING_V2"] = "true"



load_dotenv()


api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY environment variable not set. Please set it to use the chat feature.")
    

DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"  

SYSTEM_PROMPT = (
    "You are a FinOps assistant. Answer using ONLY the provided context chunks. "
    "If you see resources with 'unassigned' ownership, highlight this as a problem that needs fixing "
    "and reference FinOps guidance about proper tagging. "
    "Be specific about cost impacts when possible. "
    "Be concise and cite the source ids you used in the answer."
)

FEW_SHOT = [
    {
        "q": "What should I do with idle resources?",
        "a": "Terminate or stop resources idle >30 days; estimate savings by current monthly cost × 0.7. [source: finops_1]"
    },
    {
        "q": "How do tags help with cost?",
        "a": "Tags let you attribute cost to teams/projects; missing tags create unknown spend and prevent accountability. [source: finops_2]"
    }
]

def _build_prompt(question, retrieved):
    # Build a user message that includes retrieved contexts 
    chunks_text = []
    for r in retrieved:
        sid = r.get("id")
        text = r.get("text")
        chunks_text.append(f"[{sid}] {text}")
    context_block = "\n\n".join(chunks_text) if chunks_text else ""
    few_shot_block = "\n\n".join([f"Q: {fs['q']}\nA: {fs['a']}" for fs in FEW_SHOT])
    user_msg = (
        f"{few_shot_block}\n\nContext:\n{context_block}\n\nQuestion: {question}\n\n"
        "Answer concisely and include source ids (e.g. [finops_1] or [bill_res-23_2025-08])."
    )
    return user_msg

async def answer(question: str, top_k: int = 5, groq_model: str | None = None):
    # 1) retrieve relevant documents
    retrieved = retrieve(question, top_k=top_k)

    # 2) build prompt and messages
    user_prompt = _build_prompt(question, retrieved)
    system_msg = SystemMessage(content=SYSTEM_PROMPT)
    user_msg = HumanMessage(content=user_prompt)

    # 3) call Groq via LangChain
    model_name = groq_model if groq_model is not None else DEFAULT_GROQ_MODEL
    llm = ChatGroq(model=model_name, api_key=api_key)
    try:
        resp = llm.invoke([system_msg, user_msg])
    except Exception as e:
        # defensive fallback: return retrieved chunks and the error
        return {"answer": None, "error": str(e), "sources": retrieved}

    # parse the response — LangChain chat models often return object with .content or nested generations
    answer_text = None
    try:
        # If __call__ returned a list-like of BaseMessage
        if isinstance(resp, list) and len(resp) > 0:
            # try to extract text content
            candidate = resp[0]
            if hasattr(candidate, "content"):
                answer_text = candidate.content
            elif isinstance(candidate, dict) and "content" in candidate:
                answer_text = candidate["content"]
        else:
            # try attributes
            if hasattr(resp, "content"):
                answer_text = resp.content
            elif hasattr(resp, "generations"):
                # common pattern: resp.generations[0][0].text
                g = resp.generations
                if g and isinstance(g, list) and len(g) > 0 and len(g[0]) > 0:
                    answer_text = getattr(g[0][0], "text", None)
    except Exception:
        answer_text = None

    # final defensive fallback
    if answer_text is None:
        try:
            # try string conversion
            answer_text = str(resp)
        except Exception:
            answer_text = "<unable to parse model output>"

    return {"answer": answer_text, "sources": retrieved}
