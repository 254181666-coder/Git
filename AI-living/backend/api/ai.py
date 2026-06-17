"""
AI智能API
"""
import logging
from fastapi import APIRouter

from services.ai_driver import ai_driver
from models.schemas import AiGenerateRequest, ChatMessage, ProductInfoRequest

router = APIRouter()
logger = logging.getLogger(__name__)

product_info = ""
conversation_history = []

def _fallback_live_reply(message: str, info: str) -> str:
    """Generate a useful local reply when no LLM is configured."""
    clean_message = message.strip() or "观众提问"
    clean_info = info.strip()
    if clean_info:
        return (
            f"宝宝这个问题问得好。{clean_info} "
            f"针对“{clean_message}”，我建议大家重点看它的使用场景和到手体验，"
            "需要的可以先拍下，主播这边继续给大家详细讲。"
        )
    return (
        f"宝宝你问的是“{clean_message}”。这边建议先告诉我具体商品信息，"
        "我就能帮你生成更贴近直播间的话术；现在可以先引导大家关注价格、品质和售后。"
    )

@router.post("/chat")
async def chat(req: ChatMessage):
    """智能聊天回复"""
    active_product_info = req.product_info or product_info
    prompt = f"""你是专业的直播带货主播。商品信息：{active_product_info or "暂无"}
观众问题：{req.message}
要求：回答热情专业、突出商品优势、保持口语化，控制在80字以内。"""

    if ai_driver.is_connected("openai"):
        response = ai_driver.generate_response(prompt)
        driver = "openai"
        if not response or response.strip() == prompt.strip():
            response = _fallback_live_reply(req.message, active_product_info)
            driver = "local_fallback"
    else:
        response = _fallback_live_reply(req.message, active_product_info)
        driver = "local_fallback"

    conversation_history.extend([
        {"role": "user", "content": req.message},
        {"role": "assistant", "content": response}
    ])
    if len(conversation_history) > 20:
        del conversation_history[:-20]
    
    return {"response": response, "driver": driver, "product_info": active_product_info}

@router.post("/product")
async def set_product_info(req: ProductInfoRequest):
    """设置商品信息"""
    global product_info
    product_info = req.info.strip()
    return {"status": "ok", "product_info": product_info}

@router.get("/status")
async def get_status():
    return {
        "openai_connected": ai_driver.is_connected("openai"),
        "sadtalker_connected": ai_driver.is_connected("sadtalker")
    }
