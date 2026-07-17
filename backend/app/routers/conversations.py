"""
Conversations router
对话管理域：创建、列出、查看、删除、更新标题
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..deps import ctx, get_current_user

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# ===== Request/Response Models =====

class ConversationCreateRequest(BaseModel):
    title: str = "新对话"


class ConversationRenameRequest(BaseModel):
    title: str


# ===== Routes =====

@router.post("")
async def conversation_create(
    req: ConversationCreateRequest,
    user_id: str = Depends(get_current_user)
) -> dict:
    """创建新对话"""
    conv = ctx.conversations.create(user_id, req.title)
    return {
        "id": conv.id,
        "title": conv.title,
        "user_id": conv.user_id,
        "message_count": len(conv.messages),
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
    }


@router.get("")
async def conversation_list(
    user_id: str = Depends(get_current_user)
) -> dict:
    """列出用户的所有对话"""
    convs = ctx.conversations.list(user_id)
    return {
        "conversations": [
            {
                "id": c.id,
                "title": c.title,
                "message_count": len(c.messages),
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in convs
        ]
    }


@router.get("/{conv_id}")
async def conversation_get(
    conv_id: str,
    user_id: str = Depends(get_current_user)
) -> dict:
    """获取对话详情"""
    conv = ctx.conversations.get(conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    if conv.user_id != user_id:
        raise HTTPException(status_code=404, detail="conversation not found")

    return {
        "id": conv.id,
        "title": conv.title,
        "user_id": conv.user_id,
        "messages": conv.messages,
        "summary": conv.summary,
        "message_count": len(conv.messages),
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
    }


@router.delete("/{conv_id}")
async def conversation_delete(
    conv_id: str,
    user_id: str = Depends(get_current_user)
) -> dict:
    """删除对话"""
    conv = ctx.conversations.get(conv_id)
    if conv is None or conv.user_id != user_id:
        raise HTTPException(status_code=404, detail="conversation not found")
    return {"deleted": ctx.conversations.delete(conv_id)}


@router.put("/{conv_id}/title")
async def conversation_rename(
    conv_id: str,
    req: ConversationRenameRequest,
    user_id: str = Depends(get_current_user)
) -> dict:
    """更新对话标题"""
    conv = ctx.conversations.get(conv_id)
    if conv is None or conv.user_id != user_id:
        raise HTTPException(status_code=404, detail="conversation not found")
    ok = ctx.conversations.rename(conv_id, req.title)
    if not ok:
        raise HTTPException(status_code=404, detail="conversation not found")
    return {"id": conv_id, "title": req.title}
