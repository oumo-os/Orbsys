import uuid as _uuid
from uuid import UUID
from fastapi import APIRouter, Query
from ..core.dependencies import ActiveMember, GovWriter, DB
from ..services.commons import CommonsService
from ..schemas import (
    CreateThreadRequest, CommonsThreadResponse, CommonsThreadSummaryResponse,
    CreatePostRequest, CommonsPostResponse,
    FormalReviewRequest, FormalReviewResponse,
    CorrectDormainTagRequest,
    SponsorDraftResponse, ConfirmSponsorshipRequest, SponsorConfirmResponse,
    Paginated,
)

router = APIRouter(prefix="/commons", tags=["commons"])


@router.get("/threads", response_model=Paginated[CommonsThreadSummaryResponse])
async def list_threads(
    member: ActiveMember, db: DB,
    dormain_id: UUID | None = Query(None),
    state: str | None = Query(None),
    search: str | None = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    return await CommonsService(db).list_threads(
        _uuid.UUID(member.org_id), dormain_id, state, search, page, page_size
    )


@router.post("/threads", response_model=CommonsThreadResponse, status_code=201)
async def create_thread(body: CreateThreadRequest, member: GovWriter, db: DB):
    return await CommonsService(db).create_thread(
        _uuid.UUID(member.org_id), _uuid.UUID(member.member_id), body
    )


@router.get("/threads/{thread_id}", response_model=CommonsThreadResponse)
async def get_thread(thread_id: UUID, member: ActiveMember, db: DB):
    return await CommonsService(db).get_thread(thread_id, _uuid.UUID(member.org_id))


@router.get("/threads/{thread_id}/posts", response_model=Paginated[CommonsPostResponse])
async def list_posts(
    thread_id: UUID, member: ActiveMember, db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    return await CommonsService(db).list_posts(
        thread_id, _uuid.UUID(member.org_id), page, page_size
    )


@router.post("/threads/{thread_id}/posts", response_model=CommonsPostResponse, status_code=201)
async def create_post(thread_id: UUID, body: CreatePostRequest, member: GovWriter, db: DB):
    return await CommonsService(db).create_post(
        thread_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id), body
    )


@router.post("/threads/{thread_id}/sponsor", response_model=SponsorDraftResponse)
async def sponsor_thread(thread_id: UUID, member: GovWriter, db: DB):
    return await CommonsService(db).sponsor_thread(
        thread_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id)
    )


@router.post("/threads/{thread_id}/sponsor/confirm",
             response_model=SponsorConfirmResponse, status_code=201)
async def confirm_sponsorship(
    thread_id: UUID, body: ConfirmSponsorshipRequest, member: GovWriter, db: DB,
):
    return await CommonsService(db).confirm_sponsorship(
        thread_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id), body
    )


@router.post("/posts/{post_id}/formal-review",
             response_model=FormalReviewResponse, status_code=201)
async def formal_review(post_id: UUID, body: FormalReviewRequest, member: GovWriter, db: DB):
    return await CommonsService(db).formal_review(
        post_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id), body
    )


@router.patch("/threads/{thread_id}/dormain-tags", response_model=CommonsThreadResponse)
async def correct_dormain_tag(
    thread_id: UUID, body: CorrectDormainTagRequest, member: GovWriter, db: DB,
):
    return await CommonsService(db).correct_dormain_tag(
        thread_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id), body
    )
