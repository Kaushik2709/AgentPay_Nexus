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
    - Validates a bounded purchase vocabulary against explicit catalog families.
    - Selects one grounded product per request family; asks for clarification otherwise.
    - Evaluates upsells and enforces the Buyer Shield against unrequested accessories.
    """
    def __init__(self, agent_id: str = "agent_aarav_99"):
        self.agent_id = agent_id

    def parse_intent(self, goal_text: str, budget_cap: float) -> Dict[str, Any]:
        from app.agents.purchase_intent import parse_purchase_intent
        return parse_purchase_intent(goal_text, budget_cap)

    async def execute_catalog_discovery(self, db: AsyncSession, parsed_intent: Dict[str, Any]) -> List[Product]:
        from app.agents.purchase_intent import select_products
        products = await CatalogService.get_all_products(db)
        return select_products(products, parsed_intent)

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
