from fastapi import APIRouter, Depends, status

from telegram_engine.accounts.service import AccountService
from telegram_engine.api.deps import get_account_service
from telegram_engine.api.errors import map_domain_error
from telegram_engine.api.schemas import SendMessageRequest, SendMessageResponse

router = APIRouter(tags=["messages"])


@router.post("/send", response_model=SendMessageResponse, status_code=status.HTTP_200_OK)
async def send_message(
    payload: SendMessageRequest,
    service: AccountService = Depends(get_account_service),
) -> SendMessageResponse:
    try:
        sent = await service.send_message(payload.account, payload.to, payload.message)
    except Exception as exc:
        raise map_domain_error(exc) from exc
    return SendMessageResponse(account_id=payload.account, to=sent.chat, outbound_id=sent.outbound_id)
