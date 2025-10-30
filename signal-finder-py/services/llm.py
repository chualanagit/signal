import os, httpx, json
from typing import List, Dict
from dotenv import load_dotenv
from .models import Post, JudgeItem

# Explicitly load .env file
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

async def _responses(messages: List[Dict], http: httpx.AsyncClient, json_mode: bool = False, max_tokens: int = 900) -> str:
    payload = {
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "messages": messages
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    r = await http.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    r.raise_for_status()
    data = r.json()
    return data.get("output_text") or data.get("choices",[{}])[0].get("message",{}).get("content","")

async def _responses_stream(messages: List[Dict], http: httpx.AsyncClient, max_tokens: int = 900):
    """Stream responses from OpenAI API, yielding chunks as they arrive"""
    payload = {
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "messages": messages,
        "stream": True
    }
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    
    async with http.stream("POST", "https://api.openai.com/v1/chat/completions", headers=headers, json=payload) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]  # Remove "data: " prefix
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue

async def _search_website_info(url: str, http: httpx.AsyncClient) -> str:
    """Use Google Search API to get information about a website"""
    try:
        # Extract domain name for search
        domain = url.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
        
        # Search for information about the company/website
        search_query = f'"{domain}" company "what does" OR "about" OR "services"'
        
        KEY = os.getenv("GOOGLE_CSE_KEY", "")
        
        # We need a general web search engine ID for this to work
        # For now, let's try to get a general web custom search engine
        # You'll need to create a general web CSE at https://cse.google.com/
        GENERAL_CSE_ID = os.getenv("GOOGLE_CSE_CX_GENERAL", "")
        
        if not GENERAL_CSE_ID:
            # Fallback: use LinkedIn CSE but search more broadly
            GENERAL_CSE_ID = os.getenv("GOOGLE_CSE_CX_LINKEDIN", "")
            search_query = f"{domain} company about"
        
        params = {
            "key": KEY,
            "cx": GENERAL_CSE_ID,
            "q": search_query,
            "num": "3"
        }
        
        r = await http.get("https://www.googleapis.com/customsearch/v1", params=params)
        r.raise_for_status()
        data = r.json()
        
        # Extract snippets from search results
        snippets = []
        for item in data.get("items", [])[:3]:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            if snippet:
                snippets.append(f"{title}: {snippet}")
        
        return "\n".join(snippets) if snippets else "No search results found for this website"
        
    except Exception as e:
        # If search fails, fall back to LLM knowledge
        return f"Unable to search for current information. Using available knowledge about {url}"

# --- your function names ---
async def llmGetAppDescriptionFromWebsite(url: str, http: httpx.AsyncClient) -> str:
    # First search for information about the website
    search_info = await _search_website_info(url, http)
    
    if "Unable to search" in search_info or "Search failed" in search_info:
        # Fallback to LLM knowledge if search fails
        return await _responses([
            {"role":"system","content":"Based on your knowledge, provide an accurate, objective summary of what this company/product does in 4-6 short sentences. Focus on their core business, products, or services. Be factual and neutral. If you don't have specific knowledge, say so."},
            {"role":"user","content":f"Website: {url}\nDescribe what this company/product does based on your knowledge."}
        ], http)
    else:
        # Use search results
        return await _responses([
            {"role":"system","content":"Based on the search results provided, create an accurate, objective summary of what this company/product does in 4-6 short sentences. Focus on their core business, products, or services. Be factual and neutral based on the search information."},
            {"role":"user","content":f"Website: {url}\n\nSearch Results:\n{search_info}\n\nBased on these search results, describe what this company/product does."}
        ], http)

async def llmAnalyzeCustomerSegment(description: str, http: httpx.AsyncClient) -> str:
    return await _responses([
        {"role":"system","content":"Based on the product description, identify the primary target customer segment. Be specific about whether this is B2B (business-to-business), B2C (business-to-consumer), or B2B2C (business-to-business-to-consumer). Also specify the specific type of customers (e.g., 'Small to medium businesses', 'Enterprise companies', 'Individual consumers', 'Content creators', 'Developers', etc.). Keep response to 1-2 sentences."},
        {"role":"user","content":f"Product description: {description}\nWhat customer segment is this best suited for?"}
    ], http)

async def llmExtractPainPoints(description: str, http: httpx.AsyncClient) -> List[str]:
    text = await _responses([
        {"role":"system","content":"Extract 3-5 key pain points or problems that this product solves for customers. Focus on the customer's struggles, challenges, and frustrations - NOT product features. Return as JSON array of strings. Each pain point should be a concise phrase (5-10 words)."},
        {"role":"user","content":f"Product description: {description}\n\nWhat pain points does this product solve? Focus on customer problems, not features.\n\nGood examples:\n- 'Wasting time on manual data entry'\n- 'Struggling to collaborate across time zones'\n- 'Losing leads due to slow response times'\n- 'Spending too much on multiple disconnected tools'\n\nBad examples (too feature-focused):\n- 'AI-powered automation'\n- 'Cloud-based platform'\n- 'Real-time notifications'"}
    ], http, json_mode=True)
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Handle different response formats
            return data.get('pain_points', data.get('points', data.get('items', [])))
        return []
    except:
        return []

async def llmGenerateGtmTopicForApp(description: str, http: httpx.AsyncClient) -> List[str]:
    text = await _responses([
        {"role":"system","content":"Generate 5 GTM topics focused on customer pain points and problems this product solves, not product features. Think about what struggles, frustrations, and challenges potential customers face that this product addresses. Format as JSON array of strings."},
        {"role":"user","content":f"Product: {description}\n\nWhat customer pain points does this solve? Focus on:\n- Problems people face (not product features)\n- Frustrations this eliminates\n- Challenges this addresses\n- Struggles this makes easier\n\nExamples of GOOD pain-focused topics:\n- 'Learning to Code Struggles'\n- 'Remote Work Collaboration Challenges'\n- 'Development Environment Setup Headaches'\n- 'Getting Started with Programming Barriers'\n\nExamples of BAD feature-focused topics:\n- 'Online Coding Platforms'\n- 'Web-Based IDEs'\n- 'Multi-Language Support'"}
    ], http, json_mode=True)
    try: 
        result = json.loads(text)
        # Handle if it returns an object with topics key
        if isinstance(result, dict) and 'topics' in result:
            return result['topics']
        elif isinstance(result, list):
            return result
        else:
            return []
    except: return []

async def llmGenerateSearchKeywords(topic: str, description: str, http: httpx.AsyncClient) -> List[str]:
    text = await _responses([
        {"role":"system","content":'Generate 6-8 search queries to find BUSINESS BUYERS and DECISION-MAKERS who are actively evaluating or purchasing solutions for their company/team. Target people with BUDGET and AUTHORITY, not hobbyists or students. Focus on B2B buying intent. Return JSON {"queries":[...]} format.'},
        {"role":"user","content":f"GTM Topic: {topic}\nProduct: {description}\n\nTarget BUSINESS DECISION-MAKERS who are:\n- Evaluating solutions for their company/team (\"looking for [solution] for our company\")\n- Comparing enterprise/business tools (\"Salesforce vs HubSpot for enterprise\")\n- Have budget to spend (\"best paid tool\", \"enterprise solution\")\n- Making purchasing decisions (\"recommend for our team\", \"company looking for\")\n- Switching vendors/tools (\"migrating from\", \"replacing our current\")\n- Experiencing business pain points (\"our team struggles with\", \"company needs\")\n\nPRIORITIZE queries with:\n- \"for our company/team/business\"\n- \"enterprise\" or \"professional\"\n- Vendor/tool comparisons\n- \"looking to buy/purchase\"\n- \"budget for\"\n- Department/role mentions (\"for marketing team\", \"sales needs\")\n\nAVOID queries about:\n- Learning/tutorials (\"how to learn\", \"beginner guide\")\n- Personal/hobby use (\"for my side project\")\n- Free alternatives only\n- Student/academic use\n\nExamples:\n- \"CRM for small business looking to upgrade\"\n- \"enterprise project management tool alternatives\"\n- \"our team needs better collaboration software\"\n- \"switching from Slack to something better for remote team\""}
    ], http, json_mode=True)
    try: return json.loads(text).get("queries",[])
    except: return []

async def llmFilterPosts(topic: str, items: List[Dict[str,str]], http: httpx.AsyncClient) -> List[JudgeItem]:
    text = await _responses([
        {"role":"system","content":"Filter posts for BUSINESS BUYERS with PURCHASING POWER who are actively evaluating or buying solutions for their company/team. ONLY keep posts from people who appear to have BUDGET and DECISION-MAKING AUTHORITY. You MUST return a JSON array (list) of objects, where each object has keys: url, keep (boolean), reason (string). Even if there is only one item, wrap it in an array: [{...}]."},
        {"role":"user","content":f"GTM Topic: {topic}\n\n✅ KEEP posts from BUSINESS BUYERS who:\n- Mention their company/team/organization (\"our company\", \"my team\", \"we need\")\n- Have decision-making authority (\"I'm evaluating\", \"looking to purchase\", \"we're switching\")\n- Comparing business/enterprise tools (not hobby projects)\n- Express business pain points (\"our team struggles\", \"costing us money/time\")\n- Mention budget/investment (\"willing to pay\", \"best paid solution\", \"enterprise tier\")\n- Reference business context (\"for our sales team\", \"marketing department needs\")\n- Are actively shopping (\"comparing vendors\", \"need recommendations for [business use]\")\n\n❌ EXCLUDE posts from:\n- Students or learners (\"learning\", \"homework\", \"school project\")\n- Hobbyists or personal projects (\"my side project\", \"just for fun\")\n- People only wanting free solutions (\"free alternatives only\")\n- Tutorial seekers (\"how to\", \"tutorial\", \"getting started\")\n- General discussions without buying intent\n- News/announcements without evaluation context\n- Academic/research use (\"for my thesis\", \"university\")\n\n🎯 SIGNALS OF BUSINESS BUYER:\n- Uses \"we\", \"our\", \"team\", \"company\" language\n- Mentions specific business problems/costs\n- Comparing paid/enterprise tools\n- References existing vendors they're using\n- Asks about implementation, migration, support\n- Mentions stakeholders, budget, procurement\n\nItems to evaluate:\n" + "\n\n".join([f"Title: {i['title']}\nSnippet: {i['snippet']}\nURL: {i['url']}" for i in items])}
    ], http, json_mode=True, max_tokens=1500)
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [JudgeItem(**d) for d in data]
        elif isinstance(data, dict):
            # Handle case where response is wrapped in an object with various keys
            if 'results' in data:
                return [JudgeItem(**d) for d in data['results']]
            elif 'items' in data:
                return [JudgeItem(**d) for d in data['items']]
            # Handle case where LLM returns a single object instead of array
            elif 'url' in data and 'keep' in data:
                return [JudgeItem(**data)]
            else:
                return []
        else:
            return []
    except Exception as e:
        # If filtering fails, keep all posts
        print(f"ERROR in llmFilterPosts: {e}")
        return [JudgeItem(url=item['url'], keep=True, reason="Filter failed, keeping all") for item in items]

async def llmGenerateResponse(topic: str, post: Dict[str,str], http: httpx.AsyncClient) -> str:
    return await _responses([
        {"role":"system","content":"Write a concise, non-spammy public reply (2–3 sentences), helpful and respectful. Markdown only."},
        {"role":"user","content":f"Topic: {topic}\nTitle: {post.get('title')}\nSnippet: {post.get('snippet')}\nURL: {post.get('url')}"}
    ], http)

async def llmGenerateResponseStream(topic: str, post: Dict[str,str], http: httpx.AsyncClient):
    """Stream response generation for real-time UX"""
    async for chunk in _responses_stream([
        {"role":"system","content":"Write a concise, non-spammy public reply (2–3 sentences), helpful and respectful. Markdown only."},
        {"role":"user","content":f"Topic: {topic}\nTitle: {post.get('title')}\nSnippet: {post.get('snippet')}\nURL: {post.get('url')}"}
    ], http):
        yield chunk
