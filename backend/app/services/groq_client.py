"""
Groq LLM client for Sanctuary.
"""
import os, json, logging, httpx

logger = logging.getLogger(__name__)

# Simple in-memory cache for intent parsing
# Avoids calling Groq twice for the same query
_intent_cache: dict[str, dict] = {}

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
    # Return cached result if same query seen before
    cache_key = query.lower().strip()
    if cache_key in _intent_cache:
        logger.debug("Intent cache hit: %s", cache_key[:40])
        return _intent_cache[cache_key]

    # Skip Groq for single generic words — no LLM needed
    GENERIC = {"church","churches","chapel","chapels","worship",
               "religious","ecclesiastical","hall","halls"}
    if cache_key in GENERIC:
        result = {"locations":[],"features":[],"price_max":None,
                  "price_min":None,"size_min_sqft":None,"size_max_sqft":None,
                  "denomination":None,"use_case":None,"listing_type":None,
                  "follow_up_questions":[]}
        _intent_cache[cache_key] = result
        return result
    """
    Parse search intent.
    Groq handles: price, denomination, use_case, follow_up_questions.
    Location extracted deterministically to avoid hallucination.
    """
    import re as _re

    # Deterministic location extraction — reliable, instant, no hallucination
    # Search terms for each region — includes postcode prefixes AND place names
    # because DB stores locations as "Hackney, E8" or "Swanscombe - Kent"
    UK_PLACES = {
        "london":          ["London","E","EC","N","NW","SE","SW","W","WC",
                            "IG","RM","DA","BR","CR","SM","KT","TW","UB","HA","EN","WD",
                            "Hackney","Croydon","Greenwich","Woolwich","Bromley",
                            "Clerkenwell","Hammersmith","Fulham","Barkingside","Chingford",
                            "Sidcup","Dartford","Wandsworth","Islington","Lambeth",
                            "Southwark","Tower Hamlets","Newham","Waltham"],
        "kent":            ["Kent","CT","ME","TN","DA","Swanscombe","Dartford",
                            "Maidstone","Canterbury","Rochester","Chatham","Gravesend"],
        "yorkshire":       ["Yorkshire","BD","DN","HD","HG","HX","HU","LS","S","WF","YO",
                            "Barnsley","Leeds","Sheffield","Bradford","Hull","York",
                            "Harrogate","Wakefield","Doncaster","Huddersfield","Halifax"],
        "surrey":          ["Surrey","GU","KT","RH","SM","CR","TW","Guildford","Woking"],
        "essex":           ["Essex","CM","CO","IG","RM","SS","Chelmsford","Colchester"],
        "sussex":          ["Sussex","BN","RH","TN","Brighton","Eastbourne","Worthing"],
        "hampshire":       ["Hampshire","PO","SO","GU","Southampton","Portsmouth"],
        "lancashire":      ["Lancashire","BB","FY","LA","PR","Blackpool","Preston","Burnley"],
        "manchester":      ["Manchester","M","SK","BL","OL","WN","Salford","Stockport"],
        "midlands":        ["Midlands","B","CV","DY","WS","WV","LE","NG","DE",
                            "Birmingham","Coventry","Leicester","Nottingham","Derby"],
        "wales":           ["Wales","CF","LD","LL","NP","SA","SY",
                            "Cardiff","Swansea","Newport","Wrexham"],
        "scotland":        ["Scotland","AB","DD","EH","FK","G","KA","KY","ML","PA","PH",
                            "Edinburgh","Glasgow","Aberdeen","Dundee"],
        "devon":           ["Devon","EX","PL","TQ","Exeter","Plymouth","Torquay"],
        "cornwall":        ["Cornwall","PL","TR","Truro","Penzance","Falmouth"],
        "norfolk":         ["Norfolk","NR","Norwich"],
        "suffolk":         ["Suffolk","CO","IP","Ipswich"],
        "oxfordshire":     ["Oxfordshire","OX","Oxford"],
        "berkshire":       ["Berkshire","RG","SL","Reading","Windsor"],
        "hertfordshire":   ["Hertfordshire","AL","EN","HP","SG","WD","Watford","St Albans"],
        "cambridgeshire":  ["Cambridgeshire","CB","PE","Cambridge","Peterborough"],
        "lincolnshire":    ["Lincolnshire","LN","DN","Lincoln","Grimsby"],
        "derbyshire":      ["Derbyshire","DE","S","Derby","Chesterfield"],
        "nottinghamshire": ["Nottinghamshire","NG","Nottingham","Newark"],
        "staffordshire":   ["Staffordshire","ST","WS","Stoke","Stafford"],
        "shropshire":      ["Shropshire","SY","TF","Shrewsbury","Telford"],
        "worcestershire":  ["Worcestershire","WR","DY","Worcester"],
        "warwickshire":    ["Warwickshire","CV","Warwick","Stratford"],
        "northamptonshire":["Northamptonshire","NN","Northampton"],
        "cheshire":        ["Cheshire","CH","CW","SK","WA","Chester","Crewe"],
        "cumbria":         ["Cumbria","CA","LA","Carlisle","Kendal"],
        "durham":          ["Durham","DH","DL","SR","Sunderland","Hartlepool","Stockton"],
        "northumberland":  ["Northumberland","NE","Newcastle","Gateshead"],
        "dorset":          ["Dorset","BH","DT","Bournemouth","Poole","Weymouth"],
        "wiltshire":       ["Wiltshire","BA","SN","SP","Salisbury","Swindon"],
        "gloucestershire": ["Gloucestershire","GL","Gloucester","Cheltenham"],
        "somerset":        ["Somerset","BA","BS","TA","Bath","Taunton","Wells"],
    }

    q_lower = query.lower()
    q_words = set(_re.findall(r"[a-z]+", q_lower))

    locations = []
    for place, expansions in UK_PLACES.items():
        if place in q_words or place in q_lower:
            locations.extend(expansions)
            break  # only expand the first match to avoid over-expanding

    # Groq for everything else
    system = """Parse this UK church property search query. Return ONLY valid JSON:
{
  "price_max": null,
  "price_min": null,
  "denomination": null,
  "use_case": null,
  "listing_type": null,
  "features": [],
  "size_min_sqft": null,
  "size_max_sqft": null,
  "follow_up_questions": []
}
Price: "under 200k"->price_max:200000, "above 30k"->price_min:30000, "between 10k and 50k"->price_min:10000,price_max:50000
Features - extract these exact terms when mentioned:
  parking/car park/garage -> "parking"
  graveyard/cemetery/churchyard -> "graveyard"
  hall/meeting room/function room -> "hall"
  spire/tower/steeple -> "spire"
  listed/grade I/grade II -> "listed"
  garden/grounds/courtyard -> "garden"
  kitchen/catering -> "kitchen"
  disabled access/wheelchair -> "disabled"
Size: "1000 sqft"->size_min_sqft:1000, "large" (>3000sqft)->size_min_sqft:3000, "small" (<1000sqft)->size_max_sqft:1000
follow_up_questions: 1-2 questions specific to this query. Never generic."""

    try:
        result = await chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": query},
            ],
            temperature=0.1, max_tokens=200, json_mode=True,
        )
        data = json.loads(result)
        data["locations"] = locations
        data.setdefault("size_min_sqft", None)
        data.setdefault("size_max_sqft", None)
        data.setdefault("features", [])
        # Cache for this session
        _intent_cache[cache_key] = data
        return data
    except Exception as e:
        logger.warning("Groq intent parse failed: %s", e)
        result = {"locations": locations, "follow_up_questions": []}
        _intent_cache[cache_key] = result
        return result

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
