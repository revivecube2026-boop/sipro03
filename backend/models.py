"""All Pydantic request models for SIPRO."""
from pydantic import BaseModel
from typing import Optional, List


# ---- Auth ----
class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "sales"


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ---- Organization / Project / Unit ----
class OrganizationCreate(BaseModel):
    name: str
    type: str = "developer"
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class ProjectCreate(BaseModel):
    name: str
    organization_id: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    total_units: int = 0
    target_revenue: float = 0
    status: str = "planning"


class UnitCreate(BaseModel):
    project_id: str
    block: str = ""
    number: str = ""
    unit_type: str = "standard"
    floor_area: float = 0
    land_area: float = 0
    price: float = 0
    status: str = "available"
    coordinates: Optional[dict] = None


# ---- Lead / CRM ----
class LeadCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    source: str = "manual"
    campaign: Optional[str] = None
    ad_set: Optional[str] = None
    ad_name: Optional[str] = None
    notes: Optional[str] = None
    project_id: Optional[str] = None
    assigned_to: Optional[str] = None
    stage: Optional[str] = None


class LeadAssignRequest(BaseModel):
    lead_ids: List[str]
    assigned_to: str
    reason: Optional[str] = None


class LeadAssignmentResponse(BaseModel):
    lead_id: str
    action: str  # accept, reject
    reason: Optional[str] = None


class LeadActivityCreate(BaseModel):
    lead_id: str
    type: str
    description: str
    outcome: Optional[str] = None


# ---- Appointment / Deal ----
class AppointmentCreate(BaseModel):
    lead_id: str
    project_id: Optional[str] = None
    scheduled_at: str
    location: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class DealCreate(BaseModel):
    lead_id: Optional[str] = None
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    unit_id: str
    project_id: str
    price: float
    payment_method: str = "cash"
    notes: Optional[str] = None


# ---- WhatsApp / Dev Report / Siteplan ----
class WhatsAppMessageCreate(BaseModel):
    recipient_phone: str
    recipient_name: Optional[str] = None
    message: str
    message_type: str = "notification"
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None


class DevReportItemCreate(BaseModel):
    module: str
    feature: str
    status: str = "not_started"
    priority: str = "medium"
    notes: Optional[str] = None
    milestone: Optional[str] = None
    blockers: Optional[str] = None


class SiteplanNodeCreate(BaseModel):
    project_id: str
    unit_id: Optional[str] = None
    label: str
    x: float = 0
    y: float = 0
    width: float = 60
    height: float = 40
    shape: str = "rect"
    rotation: float = 0


# ---- Finance ----
class BillingScheduleCreate(BaseModel):
    deal_id: str
    unit_id: str
    project_id: str
    customer_name: str
    items: List[dict] = []


class PaymentCreate(BaseModel):
    deal_id: str
    billing_item_id: Optional[str] = None
    amount: float
    payment_date: str
    payment_method: str = "transfer"
    reference: Optional[str] = None
    notes: Optional[str] = None


# ---- Construction ----
class ConstructionPhaseCreate(BaseModel):
    project_id: str
    unit_id: str
    phase_name: str
    weight: float = 0
    tasks: List[dict] = []


class ConstructionProgressUpdate(BaseModel):
    unit_id: str
    phase_id: str
    task_id: Optional[str] = None
    status: str
    notes: Optional[str] = None
    photo_url: Optional[str] = None


# ---- Notification ----
class NotificationCreate(BaseModel):
    title: str
    message: str
    type: str = "info"
    target_user: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None


class AutoFollowUpRuleCreate(BaseModel):
    name: str
    trigger_event: str
    delay_minutes: int = 5
    message_template: str
    channel: str = "whatsapp"
    is_active: bool = True


# ---- Phase C: Task Engine ----
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: str = "custom"
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = "medium"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    outcome: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None


class TaskComplete(BaseModel):
    outcome: Optional[str] = None


class TaskPermissionsUpdate(BaseModel):
    allowed_roles: List[str] = ["super_admin", "marketing_admin", "marketing_inhouse", "sales"]


# ---- Phase E: Customer & Commission ----
class CustomerCreate(BaseModel):
    name: str
    nik: Optional[str] = None
    npwp: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    birthplace: Optional[str] = None
    birthdate: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    occupation: Optional[str] = None
    company: Optional[str] = None
    monthly_income: Optional[float] = None
    spouse_name: Optional[str] = None
    spouse_nik: Optional[str] = None
    spouse_phone: Optional[str] = None
    heir_name: Optional[str] = None
    heir_relation: Optional[str] = None
    heir_phone: Optional[str] = None
    notes: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    nik: Optional[str] = None
    npwp: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    birthplace: Optional[str] = None
    birthdate: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    occupation: Optional[str] = None
    company: Optional[str] = None
    monthly_income: Optional[float] = None
    spouse_name: Optional[str] = None
    spouse_nik: Optional[str] = None
    spouse_phone: Optional[str] = None
    heir_name: Optional[str] = None
    heir_relation: Optional[str] = None
    heir_phone: Optional[str] = None
    notes: Optional[str] = None


class CommissionRuleCreate(BaseModel):
    name: str
    project_id: Optional[str] = None
    role: Optional[str] = None
    rate_type: str = "percent"
    rate_value: float = 0
    tiers: Optional[List[dict]] = None
    is_active: bool = True
    priority: int = 0


class CommissionRuleUpdate(BaseModel):
    name: Optional[str] = None
    project_id: Optional[str] = None
    role: Optional[str] = None
    rate_type: Optional[str] = None
    rate_value: Optional[float] = None
    tiers: Optional[List[dict]] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class CommissionPayout(BaseModel):
    payout_date: str
    reference: Optional[str] = None
    notes: Optional[str] = None


# ---- Phase F1: Document Workflow ----
class DocumentTemplateCreate(BaseModel):
    code: str  # SPK, PPJB, AJB, BAST, CUSTOM
    name: str
    description: Optional[str] = None
    content: str  # markdown/plain text with {{variable.path}} placeholders
    variables: List[str] = []  # documented var list, e.g. ["customer.name", "unit.label"]
    is_active: bool = True


class DocumentTemplateUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = None


class DocumentCreate(BaseModel):
    template_id: str
    deal_id: str
    title: Optional[str] = None
    overrides: Optional[dict] = None  # manual variable overrides


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None  # only editable in draft status


class DocumentSign(BaseModel):
    role: str  # buyer, seller, witness
    name: str
    signature_image: str  # base64 data URL
