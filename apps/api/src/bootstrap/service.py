"""
Bootstrap orchestration service.

Handles the full first-run sequence:
  1. Create org from template
  2. Seed Dormains
  3. Register first operator (becomes founding pool member)
  4. On vSTF completion: evaluate founding circle candidacy
  5. On founding circle quorum: seed founding proposals as pre-sponsored Cells
  6. Monitor mandatory proposals → surface bootstrap_complete proposal when ready

This service is called by the first-run API routes.
It uses the same underlying service methods as normal governance — no special paths.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.events import EventType, GovernanceEvent, get_event_bus
from ..core.exceptions import Forbidden, NotFound
from ..models.org import (
    Circle, CircleDormain, CircleMember,
    Dormain, Member, Org, OrgParameter,
)
from ..models.governance import (
    Cell, CellInvitedCircle,
    CommonsPost, CommonsThread, CommonsThreadDormainTag,
    Motion, MotionDirective,
)
from ..models.types import (
    CellState, CellType, MandateType, MemberState, MotionType, TagSource,
)
from ..services.base import BaseService
from ..bootstrap.templates import (
    OrgTemplate, FoundingProposal,
    UNIVERSAL_DORMAINS,
    all_proposals_for_template,
    founding_circle_quorum,
    get_template,
)


SYSTEM_HANDLE = "_system"


class BootstrapService(BaseService):
    """
    Orchestrates first-run org creation from a template.
    Called from POST /setup endpoints only.
    """

    # ── Step 1: create org + dormains ─────────────────────────────────────────

    async def create_from_template(
        self,
        template_key: str,
        org_size: int,
        first_member_handle: str,
        first_member_display_name: str,
        first_member_email: str,
        first_member_password: str,
    ) -> dict:
        """
        Creates the org, seeds Dormains and parameters from the template,
        registers the first member.  Returns org_id and the first member's
        credentials so the frontend can log them in immediately.
        """
        tmpl = get_template(template_key)
        if tmpl is None:
            raise NotFound("Template", template_key)

        from ..core.security import hash_password

        now = datetime.now(timezone.utc)

        # Org
        org = Org(
            name=f"New {tmpl.label} Org",
            slug=f"new-org-{uuid.uuid4().hex[:6]}",
            purpose=(
                f"Organisation bootstrapped from the '{tmpl.label}' template. "
                f"The founding circle will define the permanent identity."
            ),
            bootstrapped_at=None,
            created_at=now,
        )
        self.db.add(org)
        await self.db.flush()

        # Dormains
        dormain_map: dict[str, uuid.UUID] = {}
        for spec in UNIVERSAL_DORMAINS:
            d = Dormain(
                org_id=org.id,
                name=spec["name"],
                description=spec["description"],
                decay_fn="exponential",
                decay_half_life_months=spec.get("decay_half_life_months", 18),
                decay_floor_pct=0.30,
                created_at=now,
            )
            self.db.add(d)
            await self.db.flush()
            dormain_map[spec["name"]] = d.id

        # Org parameters from template
        base_params: dict[str, Any] = {
            "membership_policy":      "open_application",
            "novice_slot_floor_pct":  0.30,
            "pass_threshold_pct":     0.50,
            "quorum_pct":             0.50,
            "stf_min_size":           3,
            "stf_max_size":           9,
            "stf_rotation_weeks_min": 2,
            "stf_rotation_weeks_max": 12,
            "commons_visibility":     "members_only",
            "c_max":                  120.0,
            "t_audit":                50.0,
            "founding_circle_quorum_min":    founding_circle_quorum(org_size)[0],
            "founding_circle_quorum_target": founding_circle_quorum(org_size)[1],
            "org_template":           template_key,
            "org_size_estimate":      org_size,
        }
        base_params.update(tmpl.parameters)

        for param, val in base_params.items():
            self.db.add(OrgParameter(
                org_id=org.id,
                parameter=param,
                value={"value": val},
                applied_at=now,
            ))

        # First member — also creates the linked PlatformAccount, since
        # /setup/create is now the platform's primary signup surface for
        # someone starting a brand new org from scratch.
        from ..models.org import PlatformAccount
        from sqlalchemy import or_ as _or

        platform_account = (await self.db.execute(
            select(PlatformAccount).where(
                _or(PlatformAccount.handle == first_member_handle,
                    PlatformAccount.email == first_member_email)
            )
        )).scalar_one_or_none()

        if platform_account is None:
            platform_account = PlatformAccount(
                handle=first_member_handle,
                email=first_member_email,
                password_hash=hash_password(first_member_password),
                created_at=now,
            )
            self.db.add(platform_account)
            await self.db.flush()
        else:
            from ..core.security import verify_password
            from ..core.exceptions import Forbidden as _Forbidden
            if not verify_password(first_member_password, platform_account.password_hash):
                raise _Forbidden(
                    "A platform account with this handle/email already exists. "
                    "Log in first, then create the org from your dashboard."
                )

        member = Member(
            org_id=org.id,
            handle=first_member_handle,
            display_name=first_member_display_name,
            email=first_member_email,
            password_hash=hash_password(first_member_password),
            platform_account_id=platform_account.id,
            joined_at=now,
            current_state=MemberState.PROBATIONARY,
        )
        self.db.add(member)
        await self.db.flush()

        await get_event_bus().emit(
            org.id,
            GovernanceEvent(
                event_type=EventType.ORG_CREATED,
                subject_id=org.id,
                subject_type="org",
                payload={
                    "name": org.name,
                    "template": template_key,
                    "org_size_estimate": org_size,
                },
            ),
        )

        return {
            "org_id": str(org.id),
            "org_slug": org.slug,
            "member_id": str(member.id),
            "platform_account_id": str(platform_account.id),
            "template": template_key,
            "dormain_map": {k: str(v) for k, v in dormain_map.items()},
            "fc_quorum": {
                "min": founding_circle_quorum(org_size)[0],
                "target": founding_circle_quorum(org_size)[1],
            },
        }

    # ── Step 5: seed founding proposals ───────────────────────────────────────

    async def seed_founding_proposals(self, org_id: uuid.UUID) -> list[str]:
        """
        Called once the founding circle reaches quorum.
        Seeds one Cell per founding proposal, authored and pre-sponsored by the system.
        Returns list of cell_ids created.
        """
        now = datetime.now(timezone.utc)

        # Find the founding circle
        fc_row = (await self.db.execute(
            select(Circle).where(
                Circle.org_id == org_id,
                Circle.founding_circle.is_(True),
                Circle.dissolved_at.is_(None),
            )
        )).scalar_one_or_none()
        if fc_row is None:
            raise Forbidden("FOUNDING_CIRCLE_NOT_FOUND")

        # Load template key
        tmpl_param = (await self.db.execute(
            select(OrgParameter).where(
                OrgParameter.org_id == org_id,
                OrgParameter.parameter == "org_template",
            )
        )).scalar_one_or_none()
        template_key = (tmpl_param.value or {}).get("value", "community") if tmpl_param else "community"
        proposals = all_proposals_for_template(template_key)

        # System member placeholder — use org's first member as nominal author
        first_member = (await self.db.execute(
            select(Member).where(
                Member.org_id == org_id,
                Member.current_state != MemberState.EXITED,
            ).order_by(Member.joined_at)
        )).scalar_one_or_none()
        if first_member is None:
            raise Forbidden("NO_MEMBERS")

        cell_ids: list[str] = []

        for proposal in proposals:
            # Skip bootstrap_complete — surfaces conditionally later
            if proposal.key == "bootstrap_complete":
                continue

            # Create Commons thread (pre-authored by system)
            thread = CommonsThread(
                org_id=org_id,
                title=proposal.title,
                body=proposal.mandate,
                author_id=first_member.id,
                state="sponsored",   # already sponsored
                created_at=now,
            )
            self.db.add(thread)
            await self.db.flush()

            # Tag thread dormains
            gov_dormain = (await self.db.execute(
                select(Dormain).where(
                    Dormain.org_id == org_id,
                    Dormain.name.in_(proposal.dormain_keys),
                )
            )).scalars().all()

            for d in gov_dormain:
                self.db.add(CommonsThreadDormainTag(
                    thread_id=thread.id,
                    dormain_id=d.id,
                    source="system",
                    tagged_at=now,
                ))

            # Create the Cell — open access, system-authored
            cell = Cell(
                org_id=org_id,
                cell_type=CellType.DELIBERATION,
                state=CellState.ACTIVE,
                access="open",
                founding_mandate=proposal.mandate,
                initiating_member_id=first_member.id,
                commons_thread_id=thread.id,
                created_at=now,
                metadata_json={
                    "bootstrap_proposal_key": proposal.key,
                    "authored_by": "system",
                    "mandatory": proposal.mandatory,
                    "sequence": proposal.sequence,
                    "pre_sponsored": True,
                },
            )
            self.db.add(cell)
            await self.db.flush()

            # Invite founding circle to the cell
            self.db.add(CellInvitedCircle(
                cell_id=cell.id,
                circle_id=fc_row.id,
                invited_at=now,
            ))

            # Seed the opening post in Commons with the full mandate text
            self.db.add(CommonsPost(
                thread_id=thread.id,
                author_id=first_member.id,
                body=(
                    f"**[System — founding proposal #{proposal.sequence // 10}]**\n\n"
                    f"{proposal.mandate}\n\n"
                    f"_This proposal was seeded automatically at bootstrap. "
                    f"The founding circle should deliberate and file a motion. "
                    f"All members can contribute to this discussion._"
                ),
                created_at=now,
            ))

            await self.db.flush()
            cell_ids.append(str(cell.id))

            await get_event_bus().emit(
                org_id,
                GovernanceEvent(
                    event_type=EventType.CELL_CREATED,
                    subject_id=cell.id,
                    subject_type="cell",
                    payload={
                        "bootstrap_proposal_key": proposal.key,
                        "pre_sponsored": True,
                        "invited_circle_ids": [str(fc_row.id)],
                    },
                ),
            )

        return cell_ids

    # ── Founding circle candidacy (called from Inferential after vSTF) ────────

    async def evaluate_fc_candidacy(
        self,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        fc_recommendation: bool,
        vstf_id: uuid.UUID,
    ) -> bool:
        """
        Record a founding circle candidacy recommendation.
        If the founding circle has reached quorum, form it and seed proposals.
        Returns True if the founding circle was just formed.
        """
        now = datetime.now(timezone.utc)

        # Store the recommendation in a dedicated parameter
        key = f"fc_candidate_{member_id}"
        self.db.add(OrgParameter(
            org_id=org_id,
            parameter=key,
            value={"value": fc_recommendation, "vstf_id": str(vstf_id)},
            applied_at=now,
        ))
        await self.db.flush()

        if not fc_recommendation:
            return False

        # Count confirmed candidates so far
        rows = (await self.db.execute(
            select(OrgParameter).where(
                OrgParameter.org_id == org_id,
                OrgParameter.parameter.like("fc_candidate_%"),
            )
        )).scalars().all()
        confirmed = [r for r in rows if (r.value or {}).get("value") is True]

        # Check quorum parameters
        min_param = (await self.db.execute(
            select(OrgParameter).where(
                OrgParameter.org_id == org_id,
                OrgParameter.parameter == "founding_circle_quorum_min",
            )
        )).scalar_one_or_none()
        quorum_min = int((min_param.value or {}).get("value", 3)) if min_param else 3

        if len(confirmed) < quorum_min:
            return False

        # Check founding circle doesn't already exist
        existing_fc = (await self.db.execute(
            select(Circle).where(
                Circle.org_id == org_id,
                Circle.founding_circle.is_(True),
            )
        )).scalar_one_or_none()
        if existing_fc:
            # Just add the new candidate to existing founding circle
            if len(confirmed) <= 13:  # FC_MAX
                already = (await self.db.execute(
                    select(CircleMember).where(
                        CircleMember.circle_id == existing_fc.id,
                        CircleMember.member_id == member_id,
                    )
                )).scalar_one_or_none()
                if not already:
                    self.db.add(CircleMember(
                        circle_id=existing_fc.id,
                        member_id=member_id,
                        joined_at=now,
                        current_state=MemberState.ACTIVE,
                    ))
                    await self.db.flush()
            return False

        # Form the founding circle from all confirmed candidates
        gov_dormain = (await self.db.execute(
            select(Dormain).where(
                Dormain.org_id == org_id,
                Dormain.name == "Governance",
            )
        )).scalar_one_or_none()

        fc = Circle(
            org_id=org_id,
            name="Founding Circle",
            description="Temporary governing body formed at bootstrap. Dissolves on founding resolution.",
            founding_circle=True,
            created_at=now,
        )
        self.db.add(fc)
        await self.db.flush()

        if gov_dormain:
            self.db.add(CircleDormain(
                circle_id=fc.id,
                dormain_id=gov_dormain.id,
                mandate_type=MandateType.PRIMARY,
                added_at=now,
            ))

        # Add all confirmed candidates as founding circle members
        candidate_member_ids = [
            uuid.UUID(r.parameter.replace("fc_candidate_", ""))
            for r in confirmed
        ]
        for mid in candidate_member_ids:
            self.db.add(CircleMember(
                circle_id=fc.id,
                member_id=mid,
                joined_at=now,
                current_state=MemberState.ACTIVE,
            ))

        await self.db.flush()

        # Seed proposals
        await self.seed_founding_proposals(org_id)

        await get_event_bus().emit(
            org_id,
            GovernanceEvent(
                event_type=EventType.MEMBER_STATE_CHANGED,
                subject_id=fc.id,
                subject_type="circle",
                payload={
                    "event": "founding_circle_formed",
                    "member_count": len(candidate_member_ids),
                },
            ),
        )

        return True

    # ── Check if bootstrap_complete proposal should be surfaced ───────────────

    async def check_surface_bootstrap_proposal(self, org_id: uuid.UUID) -> bool:
        """
        Returns True if mandatory founding proposals are resolved
        and the bootstrap_complete Cell should now be seeded.
        """
        # Check if bootstrap_complete cell already exists
        existing = (await self.db.execute(
            select(Cell).where(
                Cell.org_id == org_id,
                Cell.metadata_json["bootstrap_proposal_key"].astext == "bootstrap_complete",
            )
        )).scalar_one_or_none()
        if existing:
            return False

        # Check all mandatory proposals (except bootstrap_complete) are enacted
        tmpl_param = (await self.db.execute(
            select(OrgParameter).where(
                OrgParameter.org_id == org_id,
                OrgParameter.parameter == "org_template",
            )
        )).scalar_one_or_none()
        template_key = (tmpl_param.value or {}).get("value", "community") if tmpl_param else "community"
        proposals = all_proposals_for_template(template_key)
        mandatory_keys = {
            p.key for p in proposals
            if p.mandatory and p.key != "bootstrap_complete"
        }

        # For each mandatory key, check if there is an enacted Resolution
        # referencing a Cell with that bootstrap_proposal_key
        for key in mandatory_keys:
            cell_row = (await self.db.execute(
                select(Cell).where(
                    Cell.org_id == org_id,
                    Cell.metadata_json["bootstrap_proposal_key"].astext == key,
                )
            )).scalar_one_or_none()
            if not cell_row:
                return False
            # Check at least one motion from this cell is enacted
            motion_row = (await self.db.execute(
                select(Motion).where(
                    Motion.cell_id == cell_row.id,
                    Motion.state == "enacted_locked",
                )
            )).scalar_one_or_none()
            if not motion_row:
                return False

        # All mandatory proposals resolved — seed the bootstrap_complete Cell
        await self._seed_bootstrap_complete_cell(org_id)
        return True

    async def _seed_bootstrap_complete_cell(self, org_id: uuid.UUID) -> None:
        """Seed the final bootstrap_complete founding proposal."""
        from ..bootstrap.templates import COMMON_PROPOSALS
        proposal = next(
            (p for p in COMMON_PROPOSALS if p.key == "bootstrap_complete"), None
        )
        if not proposal:
            return

        now = datetime.now(timezone.utc)
        first_member = (await self.db.execute(
            select(Member).where(
                Member.org_id == org_id,
                Member.current_state != MemberState.EXITED,
            ).order_by(Member.joined_at)
        )).scalar_one_or_none()
        if not first_member:
            return

        fc = (await self.db.execute(
            select(Circle).where(
                Circle.org_id == org_id,
                Circle.founding_circle.is_(True),
                Circle.dissolved_at.is_(None),
            )
        )).scalar_one_or_none()
        if not fc:
            return

        thread = CommonsThread(
            org_id=org_id,
            title=proposal.title,
            body=proposal.mandate,
            author_id=first_member.id,
            state="sponsored",
            created_at=now,
        )
        self.db.add(thread)
        await self.db.flush()

        cell = Cell(
            org_id=org_id,
            cell_type=CellType.DELIBERATION,
            state=CellState.ACTIVE,
            access="open",
            founding_mandate=proposal.mandate,
            initiating_member_id=first_member.id,
            commons_thread_id=thread.id,
            created_at=now,
            metadata_json={
                "bootstrap_proposal_key": "bootstrap_complete",
                "authored_by": "system",
                "mandatory": True,
                "sequence": 999,
                "pre_sponsored": True,
            },
        )
        self.db.add(cell)
        await self.db.flush()

        self.db.add(CellInvitedCircle(
            cell_id=cell.id,
            circle_id=fc.id,
            invited_at=now,
        ))
        self.db.add(CommonsPost(
            thread_id=thread.id,
            author_id=first_member.id,
            body=(
                "**[System — founding proposal — FINAL]**\n\n"
                + proposal.mandate
                + "\n\n_All mandatory founding proposals have been resolved. "
                "This Cell is now open for the founding circle to file the "
                "bootstrap completion motion._"
            ),
            created_at=now,
        ))
        await self.db.flush()
