"""
Groq LLM client for Sanctuary.
"""
import os, json, logging, httpx

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

def get_api_key() -> str:
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        raise ValueError("GROQ_API_KEY not set")
    return key

async def chat(messages, temperature=0.7, max_tokens=1000, json_mode=False) -> str:
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json",
    }
    body = {"model": MODEL, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(GROQ_API_URL, headers=headers, json=body)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

async def parse_search_intent(query: str) -> dict:
    system = """You are a UK property search assistant specialising in churches and chapels.
Parse the user query and return ONLY valid JSON:
{
  "locations": [],
  "price_max": null,
  "price_min": null,
  "features": [],
  "property_type": null,
  "use_case": null,
  "listing_type": null,
  "denomination": null,
  "follow_up_questions": []
}
follow_up_questions must be 1-2 questions directly relevant to what the user said.
Never ask generic questions. Always relate to their specific query."""
    try:
        result = await chat(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": query}],
            temperature=0.3, max_tokens=500, json_mode=True,
        )
        return json.loads(result)
    except Exception as e:
        logger.warning("Groq intent parse failed: %s", e)
        return {"follow_up_questions": []}

async def generate_enquiry(property_data: dict, user_intent: dict = None, user_description: str = None) -> str:
    title    = property_data.get("title", "the property")
    price    = property_data.get("price", "")
    location = property_data.get("location", "")
    source   = property_data.get("source", "")
    desc     = (property_data.get("description", "") or "")[:600]

    intent_context = ""
    if user_intent:
        parts = []
        if user_intent.get("use_case"):
            parts.append(f"intended use: {user_intent['use_case']}")
        if user_intent.get("features"):
            parts.append(f"key requirements: {', '.join(user_intent['features'])}")
        if user_intent.get("price_max"):
            parts.append(f"budget: up to £{user_intent['price_max']:,}")
        if parts:
            intent_context = f"Buyer requirements: {'; '.join(parts)}."
    if user_description:
        intent_context += f" Buyer says: {user_description}"

    system = """You are a professional UK property buyer's agent.
Write a concise professional enquiry email about a church or chapel property.
- Addressed to the selling agent (not by name)
- Show genuine knowledge of the specific property
- Ask 2-3 relevant questions based on the property description
- Professional, polite, British tone
- 150-200 words maximum
- Include subject line prefixed with Subject:
Do NOT include placeholder text like [Your Name]."""

    user_msg = f"Property: {title}\nLocation: {location}\nPrice: {price}\nSource: {source}\nDescription: {desc}\n\n{intent_context}\n\nWrite the enquiry email."

    try:
        return await chat(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
            temperature=0.7, max_tokens=400,
        )
    except Exception as e:
        logger.warning("Groq enquiry failed: %s", e)
        return ""

async def continue_dialogue(query: str, conversation_history: list, current_filters: dict) -> dict:
    system = """You are a conversational UK church property search assistant.
Help users find churches, chapels and places of worship for sale.
Ask one focused follow-up question at a time.
When you have enough info, set ready_to_search to true.
Return ONLY valid JSON:
{
  "response": "your conversational reply",
  "updated_filters": {},
  "ready_to_search": false,
  "suggested_query": ""
}"""
    messages = [{"role": "system", "content": system}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": query})
    try:
        result = await chat(messages=messages, temperature=0.7, max_tokens=300, json_mode=True)
        return json.loads(result)
    except Exception as e:
        logger.warning("Groq dialogue failed: %s", e)
        return {"response": "Could you tell me more about what you are looking for?", "updated_filters": {}, "ready_to_search": False}
