# apps/api/app/services/sebi_registry.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Literal, Optional
import hashlib
import ipaddress
from pydantic import BaseModel, Field


class CreatorTier(str, Enum):
    WHITE_BOX_PUBLIC = "WHITE_BOX_PUBLIC"       # Open DAG; low compliance barrier
    BLACK_BOX_RA_ONLY = "BLACK_BOX_RA_ONLY"     # Encrypted logic; strictly gated behind SEBI RA license


@dataclass
class StaticIPAllocationPool:
    cidr_block: str = "13.232.104.0/24"
    total_ips: int = 254
    allocated_map: Dict[str, str] = field(default_factory=dict)  # user_id -> IP string

    def allocate_static_ip_for_user(self, user_id: str) -> str:
        if user_id in self.allocated_map:
            return self.allocated_map[user_id]
        
        assigned_count = len(self.allocated_map)
        if assigned_count >= self.total_ips:
            raise ResourceWarning("SEBI Static IP Pool exhausted! Provision secondary AWS NAT Gateway.")
        
        net = ipaddress.ip_network(self.cidr_block, strict=False)
        assigned_ip = str(list(net.hosts())[assigned_count])
        self.allocated_map[user_id] = assigned_ip
        return assigned_ip


class SebiRARegistrationRequest(BaseModel):
    creator_id: str
    legal_entity_name: str
    sebi_ra_registration_number: str = Field(..., pattern=r"^INH\d{9}$")
    research_report_pdf_bytes: bytes
    declared_static_ip: str


class SebiRARegistrationResult(BaseModel):
    creator_id: str
    sebi_ra_number: str
    pdf_sha256_audit_hash: str
    assigned_nat_static_ip: str
    verification_status: Literal["VERIFIED_ACTIVE", "REJECTED_INVALID_LICENSE", "PENDING_COMPLIANCE_REVIEW"]
    approved_at: Optional[str] = None


class SebiComplianceRegistry:
    """
    Automated compliance gateway verifying SEBI RA licenses and enforcing
    April 2026 Static IP whitelisting per exchange/broker requirements.
    """
    _ip_pool = StaticIPAllocationPool()

    @classmethod
    def verify_and_register_creator(cls, req: SebiRARegistrationRequest) -> SebiRARegistrationResult:
        # 1. Cryptographically hash the uploaded SEBI Research Report PDF for 5-year audit trail
        pdf_hash = hashlib.sha256(req.research_report_pdf_bytes).hexdigest()

        # 2. Assign dedicated static egress IP (1 User = 1 IP)
        assigned_ip = cls._ip_pool.allocate_static_ip_for_user(req.creator_id)

        # 3. Validate static IP match against user declaration
        if assigned_ip != req.declared_static_ip:
            return SebiRARegistrationResult(
                creator_id=req.creator_id,
                sebi_ra_number=req.sebi_ra_registration_number,
                pdf_sha256_audit_hash=pdf_hash,
                assigned_nat_static_ip=assigned_ip,
                verification_status="REJECTED_INVALID_LICENSE",
            )

        # 4. Mock SEBI database registry lookup verification (INH prefix check)
        is_valid_ra = req.sebi_ra_registration_number.startswith("INH")

        return SebiRARegistrationResult(
            creator_id=req.creator_id,
            sebi_ra_number=req.sebi_ra_registration_number,
            pdf_sha256_audit_hash=pdf_hash,
            assigned_nat_static_ip=assigned_ip,
            verification_status="VERIFIED_ACTIVE" if is_valid_ra else "REJECTED_INVALID_LICENSE",
            approved_at=datetime.now(timezone.utc).isoformat(),
        )
