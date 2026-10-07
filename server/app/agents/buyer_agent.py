import re
from typing import List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.catalog.catalog_service import CatalogService
from app.db.models import Product

# Initialize Hugging Face models at module level lazily
_chat_model = None
_embeddings_model = None

def get_chat_model():
    global _chat_model
    if _chat_model is None:
        from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
        llm = HuggingFacePipeline.from_model_id(
            model_id="HuggingFaceTB/SmolLM-135M-Instruct",
            task="text-generation",
            pipeline_kwargs={"max_new_tokens": 50, "temperature": 0.1, "do_sample": False},
        )
        _chat_model = ChatHuggingFace(llm=llm)
    return _chat_model

def get_embeddings_model():
    global _embeddings_model
    if _embeddings_model is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings_model = HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')
    return _embeddings_model

class BuyerAgent:
    """
    Consumer Advocate Worker Agent.
    - Parses natural language purchase goals into machine-readable MCP queries.
    - Discovers matching products via MCP catalog protocol with strict whole-word semantic matching.
    - Evaluates upsells and enforces the Buyer Shield against unrequested accessories.
    """
    def __init__(self, agent_id: str = "agent_aarav_99"):
        self.agent_id = agent_id

    def parse_intent(self, goal_text: str, budget_cap: float) -> Dict[str, Any]:
        """Parses user intent from natural language using a small parameter Hugging Face model."""
        goal_lower = goal_text.lower()
        
        # Extract explicit numeric budget if present in text
        price_match = re.search(r'(?:under|below|max|budget|within|upto|up to|less than)\s*(?:₹|inr|rs\.?|rs)?\s*([\d,]+)', goal_lower)
        parsed_budget = budget_cap
        if price_match:
            try:
                parsed_budget = float(price_match.group(1).replace(",", ""))
            except ValueError:
                pass

        # Use ChatHuggingFace to understand categories
        chat_model = get_chat_model()
        from langchain_core.messages import HumanMessage, SystemMessage
        prompt = f"Given the user query '{goal_lower}', which of these categories is most relevant? Categories: monitors, keyboards, mice, subscriptions, electronics, accessories. Output only the category name."
        messages = [
            SystemMessage(content="You are a helpful assistant that classifies user queries into categories."),
            HumanMessage(content=prompt)
        ]
        res = chat_model.invoke(messages)
        content = res.content.lower()
        
        target_categories = []
        for cat in ["monitors", "keyboards", "mice", "subscriptions", "electronics", "accessories"]:
            if cat in content:
                target_categories.append(cat)

        return {
            "target_categories": target_categories,
            "target_skus": [],
            "specs_filter": {},
            "effective_budget": parsed_budget,
            "raw_goal": goal_text
        }

    async def call_database_mcp(self, db: AsyncSession, query: str, budget: float, categories: List[str]) -> List[Product]:
        """Simple MCP tool for Margin Site Database to semantically match the query."""
        all_products = await CatalogService.get_all_products(db)
        
        # Filter by stock and budget
        in_stock = [p for p in all_products if p.stock_quantity > 0 and (p.retail_price <= budget if budget else True)]
        
        if not in_stock:
            return []

        # Utilize langchain-huggingface HuggingFaceEmbeddings to match query with database catalog
        embeddings = get_embeddings_model()
        from sentence_transformers import util
        import torch
        
        corpus = [f"{p.name} {p.category} {p.description or ''}" for p in in_stock]
        
        query_emb = torch.tensor(embeddings.embed_query(query))
        corpus_emb = torch.tensor(embeddings.embed_documents(corpus))
        
        cosine_scores = util.cos_sim(query_emb, corpus_emb)[0]
        
        results = []
        threshold = 0.3 # Minimum similarity threshold
        for i, score in enumerate(cosine_scores):
            if score.item() > threshold:
                results.append((score.item(), in_stock[i]))
                
        results.sort(key=lambda x: x[0], reverse=True)
        matched_products = [p for score, p in results]

        # Fallback to model's predicted categories if semantic search didn't yield confident matches
        if not matched_products and categories:
            for p in in_stock:
                if p.category in categories:
                    matched_products.append(p)

        return matched_products

    async def execute_catalog_discovery(
        self,
        db: AsyncSession,
        parsed_intent: Dict[str, Any]
    ) -> List[Product]:
        """Discovers catalog items by calling the Database MCP with the structured intent."""
        raw_goal = parsed_intent.get("raw_goal", "")
        effective_budget = parsed_intent.get("effective_budget", float('inf'))
        target_categories = parsed_intent.get("target_categories", [])
        
        # Call the MCP tool
        found_products = await self.call_database_mcp(db, raw_goal, effective_budget, target_categories)

        # Deduplicate
        seen_skus = set()
        deduped = []
        for p in found_products:
            if p.sku not in seen_skus:
                seen_skus.add(p.sku)
                deduped.append(p)
                
        return deduped

    def evaluate_upsell_shield(
        self,
        offered_items: List[Dict[str, Any]],
        strict_items_only: bool,
        requested_skus: List[str]
    ) -> Tuple[bool, List[str], str]:
        """
        Buyer AI Shield.
        Rejects unrequested physical accessories if strict_items_only is True.
        Returns: (has_rejections, rejected_skus, reason)
        """
        rejected_skus = []
        for item in offered_items:
            is_unrequested = item.get("is_unrequested_upsell", False)
            sku = item.get("sku")
            if is_unrequested and strict_items_only:
                rejected_skus.append(sku)

        if rejected_skus:
            return True, rejected_skus, "USER_INTENT_STRICT_ITEMS_ONLY: Buyer AI shielded user from unrequested physical accessories."
        return False, [], "ALL_ITEMS_APPROVED"
