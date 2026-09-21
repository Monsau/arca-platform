"""Ontology write adapter — Suite-side client of the ArcaQ change-proposal API.

Architecture constraint (multi-entry-point, 2026-09-20): the ontology is fed
centrally through the Suite in addition to direct ArcaQ usage. There are
several logical entry points for the same actions, with identical permission
management propagated across the Suite.

Binding consequences:
  - ArcaQ remains the **single physical writer** (Jena/Fuseki). Suite modules
    are *clients* of ``POST /api/v1/ontology-ops/change-proposals`` — never a
    second writer, so there is a single chain of custody.
  - Authorization is **never reimplemented Suite-side**: every write call,
    whatever its entry point, is resolved by ArcaQ's central PDP. This
    adapter forwards the caller identity (``Authorization`` header) and lets
    ArcaQ decide (see ``docs/adr/ADR-006-policy-contract.md``).
  - The adapter always stamps ``entry_point="suite"`` so the immutable audit
    trail can answer "through which surface, under which identity".

Integration pattern (golden rule #2 of ``docs/epics/EPICS.md``):
``Protocol`` + ``Null`` (disabled by default) + ``Http`` (opt-in via feature
flag, short timeout, graceful degradation — never a business-flow blockage
when ArcaQ is down).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

#: The write funnel endpoint exposed by arcaq-api (ontology_ops router).
CHANGE_PROPOSALS_ENDPOINT = "/api/v1/ontology-ops/change-proposals"

#: Entry-point provenance value stamped on every Suite-originated write.
#: ArcaQ constrains this enum ("direct" | "suite") at the API and in its
#: SHACL/CI gates; the Suite side is always "suite".
SUITE_ENTRY_POINT = "suite"

#: Closed vocabularies mirrored from the ArcaQ ChangeProposalIn model.
VALID_CHANGE_TYPES = ("add_class", "add_property", "modify_label", "deprecate", "delete")
VALID_IMPACT_LEVELS = ("patch", "minor", "major")


@dataclass
class OntologyChangeProposal:
    """A proposed change to the ArcaQ ontology, in write-funnel terms.

    Field semantics mirror the ArcaQ ``ChangeProposalIn`` model; this repo
    never imports arcaq code (golden rule #1) — the contract lives in
    ``contracts/ontology/``.
    """

    change_type: str
    concept_uri: str
    impact_level: str
    description: str
    proposed_ttl: Optional[str] = None
    #: Optional explicit proposer identity. When None, ArcaQ attributes the
    #: proposal to the authenticated user behind the forwarded credentials.
    proposer: Optional[str] = None

    def validate(self) -> None:
        """Reject values outside the ArcaQ closed vocabularies before any
        network call — fail fast, close to the caller."""
        if self.change_type not in VALID_CHANGE_TYPES:
            raise ValueError(
                f"change_type must be one of {VALID_CHANGE_TYPES}, "
                f"got {self.change_type!r}"
            )
        if self.impact_level not in VALID_IMPACT_LEVELS:
            raise ValueError(
                f"impact_level must be one of {VALID_IMPACT_LEVELS}, "
                f"got {self.impact_level!r}"
            )
        if not self.concept_uri.strip():
            raise ValueError("concept_uri must be a non-empty URI")
        if len(self.description.strip()) < 5:
            raise ValueError("description must be meaningful (>= 5 chars)")


@dataclass
class OntologyWriteResult:
    """Outcome of a submission attempt — never raises into the business flow.

    ``status`` is one of:
      - ``created``   — ArcaQ accepted the proposal (HTTP 200/201);
      - ``rejected``  — ArcaQ answered with an error status (4xx/5xx);
      - ``degraded``  — ArcaQ unreachable / timeout: the business flow must
                        continue; the write is lost for audit purposes only;
      - ``disabled``  — Null adapter: ontology write is not enabled.
    """

    submitted: bool
    entry_point: str = SUITE_ENTRY_POINT
    status: str = "disabled"
    proposal_id: Optional[str] = None
    detail: str = ""
    obligations: list[dict] = field(default_factory=list)


@runtime_checkable
class OntologyWriteAdapter(Protocol):
    """Neutral interface for submitting ontology changes to ArcaQ.

    Implementations:
      - ``NullOntologyWriteAdapter`` — safe default, disabled;
      - ``ArcaqOntologyWriteAdapter`` — HTTP client, opt-in.
    """

    def submit_change(
        self,
        proposal: OntologyChangeProposal,
        authorization: Optional[str] = None,
    ) -> OntologyWriteResult:
        """Submit *proposal* to the central write funnel.

        *authorization* is the raw ``Authorization`` header value of the
        original caller (e.g. ``"Bearer <jwt>"``). It is forwarded verbatim
        so that ArcaQ's central PDP resolves permissions for the *caller's*
        identity — the Suite never substitutes its own policy decision.
        """
        ...


class NullOntologyWriteAdapter:
    """Disabled adapter (default). No network call, no exception.

    The result still carries ``entry_point="suite"`` so that audit consumers
    see a consistent provenance vocabulary even when the adapter is off.
    """

    def submit_change(
        self,
        proposal: OntologyChangeProposal,
        authorization: Optional[str] = None,
    ) -> OntologyWriteResult:
        proposal.validate()
        return OntologyWriteResult(
            submitted=False,
            status="disabled",
            detail="ontology write adapter is disabled (Null adapter)",
        )


class ArcaqOntologyWriteAdapter:
    """HTTP client for the ArcaQ change-proposal write funnel.

    Opt-in via feature flag (``ARCA_ONTOLOGY_WRITE_ADAPTER=arcaq``), short
    timeout, graceful degradation: any transport error returns a
    ``degraded`` result instead of raising, so a down ArcaQ never blocks a
    Suite business flow.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        client: "Optional[object]" = None,
    ) -> None:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("httpx is required for the ArcaQ ontology write adapter") from exc

        self._httpx = httpx
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout
        )
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "ArcaqOntologyWriteAdapter":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def submit_change(
        self,
        proposal: OntologyChangeProposal,
        authorization: Optional[str] = None,
    ) -> OntologyWriteResult:
        proposal.validate()

        # The Suite always writes through the central entry point. This is
        # not configurable: an entry_point other than "suite" would break the
        # audit-trail invariant that Suite-originated writes are traceable.
        payload: dict = {
            "change_type": proposal.change_type,
            "concept_uri": proposal.concept_uri,
            "impact_level": proposal.impact_level,
            "description": proposal.description,
            "entry_point": SUITE_ENTRY_POINT,
        }
        if proposal.proposed_ttl is not None:
            payload["proposed_ttl"] = proposal.proposed_ttl
        if proposal.proposer is not None:
            payload["proposer"] = proposal.proposer

        headers = {"Authorization": authorization} if authorization else {}

        try:
            response = self._client.post(
                CHANGE_PROPOSALS_ENDPOINT, json=payload, headers=headers
            )
        except self._httpx.HTTPError as exc:
            # Graceful degradation (golden rule #2): ArcaQ down must never
            # block the Suite business flow.
            return OntologyWriteResult(
                submitted=False,
                status="degraded",
                detail=f"ArcaQ write funnel unreachable: {exc}",
            )

        if response.status_code in (200, 201):
            body = response.json() if response.content else {}
            return OntologyWriteResult(
                submitted=True,
                status="created",
                proposal_id=body.get("id"),
                detail=f"proposal accepted by ArcaQ (HTTP {response.status_code})",
            )

        return OntologyWriteResult(
            submitted=False,
            status="rejected",
            detail=(
                f"ArcaQ write funnel returned HTTP {response.status_code}: "
                f"{response.text[:200]}"
            ),
        )
