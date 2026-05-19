"""Phase F1 — Document Workflow routes (SPK/PPJB/AJB/BAST).

Lifecycle:
    draft → finalized → signed
    draft → canceled

Templates are admin-editable, with {{variables}} resolved from deal+customer+unit+project context.
PDF generation via reportlab. Signatures stored as base64 data URLs.
"""
import io
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse

from deps import db, get_current_user, logger
from shared import SCOPED_ROLES, _can_access_lead
from models import (
    DocumentTemplateCreate, DocumentTemplateUpdate,
    DocumentCreate, DocumentUpdate, DocumentSign,
)
from pdf_utils import resolve_variables, build_document_pdf

router = APIRouter()

ADMIN_ROLES = {"super_admin", "marketing_admin", "management"}


async def _build_context_for_deal(deal_id: str) -> dict:
    """Aggregate deal + linked customer + unit + project into a single context dict."""
    deal = await db.deals.find_one({"id": deal_id}, {"_id": 0})
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    customer = None
    if deal.get("customer_id"):
        customer = await db.customers.find_one({"id": deal["customer_id"]}, {"_id": 0})
    if not customer:
        # fallback: minimal customer object from deal fields
        customer = {
            "name": deal.get("customer_name"),
            "phone": deal.get("customer_phone"),
            "email": deal.get("customer_email"),
        }
    unit = await db.units.find_one({"id": deal.get("unit_id")}, {"_id": 0}) or {}
    project = await db.projects.find_one({"id": deal.get("project_id")}, {"_id": 0}) or {}
    return {"deal": deal, "customer": customer, "unit": unit, "project": project}


# ==================== Document Templates ====================
@router.get("/document-templates")
async def list_templates(request: Request, code: Optional[str] = None):
    await get_current_user(request, db)
    query = {}
    if code:
        query["code"] = code
    items = await db.document_templates.find(query, {"_id": 0}).sort("code", 1).to_list(200)
    return {"data": items}


@router.post("/document-templates")
async def create_template(req: DocumentTemplateCreate, request: Request):
    user = await get_current_user(request, db)
    if user.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only admins can manage templates")
    now = datetime.now(timezone.utc).isoformat()
    doc = req.dict()
    doc["id"] = str(uuid.uuid4())
    doc["created_by"] = user.get("email")
    doc["created_at"] = now
    doc["updated_at"] = now
    await db.document_templates.insert_one(doc)
    doc.pop("_id", None)
    return {"data": doc}


@router.get("/document-templates/{template_id}")
async def get_template(template_id: str, request: Request):
    await get_current_user(request, db)
    t = await db.document_templates.find_one({"id": template_id}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"data": t}


@router.put("/document-templates/{template_id}")
async def update_template(template_id: str, req: DocumentTemplateUpdate, request: Request):
    user = await get_current_user(request, db)
    if user.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only admins can manage templates")
    update = {k: v for k, v in req.dict().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    update["updated_by"] = user.get("email")
    await db.document_templates.update_one({"id": template_id}, {"$set": update})
    return {"data": await db.document_templates.find_one({"id": template_id}, {"_id": 0})}


@router.delete("/document-templates/{template_id}")
async def delete_template(template_id: str, request: Request):
    user = await get_current_user(request, db)
    if user.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only admins can delete templates")
    await db.document_templates.delete_one({"id": template_id})
    return {"message": "deleted"}


# ==================== Documents ====================
@router.get("/documents")
async def list_documents(
    request: Request,
    deal_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    template_code: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    user = await get_current_user(request, db)
    query: dict = {}
    if deal_id:
        query["deal_id"] = deal_id
    if customer_id:
        query["customer_id"] = customer_id
    if template_code:
        query["template_code"] = template_code
    if status:
        query["status"] = status
    # Phase D RBAC: sales scope by linked lead/deal
    if user.get("role") in SCOPED_ROLES:
        query["created_by"] = user.get("email")
    total = await db.documents.count_documents(query)
    items = await db.documents.find(query, {"_id": 0, "content": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"data": items, "total": total}


@router.post("/documents")
async def create_document(req: DocumentCreate, request: Request):
    user = await get_current_user(request, db)
    template = await db.document_templates.find_one({"id": req.template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    context = await _build_context_for_deal(req.deal_id)

    # Sales scope: ensure user owns the related lead (if any)
    deal = context["deal"]
    if user.get("role") in SCOPED_ROLES and deal.get("lead_id"):
        lead = await db.leads.find_one({"id": deal["lead_id"]}, {"_id": 0, "assigned_to": 1})
        if lead and not _can_access_lead(user, lead):
            raise HTTPException(status_code=403, detail="Deal bukan milik Anda")

    # Merge overrides into context for variable resolution
    if req.overrides:
        for path, value in req.overrides.items():
            parts = path.split(".")
            cur = context
            for p in parts[:-1]:
                cur = cur.setdefault(p, {})
            cur[parts[-1]] = value

    resolved_content = resolve_variables(template["content"], context)
    title = req.title or f"{template['code']} - {context['customer'].get('name', '')}"

    # Generate next number per template (simple counter from existing doc count + 1)
    count = await db.documents.count_documents({"template_code": template["code"]})
    doc_number = f"{template['code']}/{datetime.now().year}/{count+1:04d}"

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "template_id": template["id"],
        "template_code": template["code"],
        "template_name": template["name"],
        "doc_number": doc_number,
        "title": title,
        "deal_id": req.deal_id,
        "customer_id": deal.get("customer_id"),
        "unit_id": deal.get("unit_id"),
        "project_id": deal.get("project_id"),
        "content": resolved_content,
        "variables_snapshot": req.overrides or {},
        "status": "draft",
        "signatures": [],
        "created_by": user.get("email"),
        "created_at": now,
        "updated_at": now,
    }
    await db.documents.insert_one(doc)
    doc.pop("_id", None)
    await db.events.insert_one({
        "id": str(uuid.uuid4()),
        "type": "document.created",
        "entity_type": "document",
        "entity_id": doc["id"],
        "data": {"template_code": template["code"], "deal_id": req.deal_id, "doc_number": doc_number},
        "created_at": now,
    })
    return {"data": doc}


@router.get("/documents/{doc_id}")
async def get_document(doc_id: str, request: Request):
    await get_current_user(request, db)
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"data": doc}


@router.put("/documents/{doc_id}")
async def update_document(doc_id: str, req: DocumentUpdate, request: Request):
    user = await get_current_user(request, db)
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft documents can be edited")
    update = {k: v for k, v in req.dict().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    update["updated_by"] = user.get("email")
    await db.documents.update_one({"id": doc_id}, {"$set": update})
    return {"data": await db.documents.find_one({"id": doc_id}, {"_id": 0})}


@router.post("/documents/{doc_id}/finalize")
async def finalize_document(doc_id: str, request: Request):
    user = await get_current_user(request, db)
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft documents can be finalized")
    now = datetime.now(timezone.utc).isoformat()
    await db.documents.update_one({"id": doc_id}, {"$set": {
        "status": "finalized", "finalized_at": now, "finalized_by": user.get("email"), "updated_at": now,
    }})
    await db.events.insert_one({
        "id": str(uuid.uuid4()),
        "type": "document.finalized",
        "entity_type": "document",
        "entity_id": doc_id,
        "data": {"by": user.get("email")},
        "created_at": now,
    })
    return {"data": await db.documents.find_one({"id": doc_id}, {"_id": 0})}


@router.post("/documents/{doc_id}/sign")
async def sign_document(doc_id: str, req: DocumentSign, request: Request):
    user = await get_current_user(request, db)
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.get("status") not in ("finalized", "signed"):
        raise HTTPException(status_code=400, detail="Document must be finalized before signing")
    if not req.signature_image or not req.signature_image.startswith("data:image"):
        raise HTTPException(status_code=400, detail="signature_image must be a base64 data URL")
    now = datetime.now(timezone.utc).isoformat()
    sig_entry = {
        "role": req.role,
        "name": req.name,
        "signature_image": req.signature_image,
        "signed_at": now,
        "signed_by_user": user.get("email"),
        "ip": request.client.host if request.client else None,
    }
    # Track all signatures + flip status to 'signed' on first signature
    await db.documents.update_one({"id": doc_id}, {
        "$push": {"signatures": sig_entry},
        "$set": {"status": "signed", "updated_at": now, "first_signed_at": doc.get("first_signed_at") or now},
    })
    await db.events.insert_one({
        "id": str(uuid.uuid4()),
        "type": "document.signed",
        "entity_type": "document",
        "entity_id": doc_id,
        "data": {"role": req.role, "name": req.name, "by": user.get("email")},
        "created_at": now,
    })
    return {"data": await db.documents.find_one({"id": doc_id}, {"_id": 0})}


@router.get("/documents/{doc_id}/pdf")
async def download_document_pdf(doc_id: str, request: Request):
    await get_current_user(request, db)
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        pdf_bytes = build_document_pdf(
            title=doc.get("title", "Document"),
            content=doc.get("content", ""),
            signatures=doc.get("signatures", []),
            doc_code=doc.get("template_code", ""),
            doc_number=doc.get("doc_number", ""),
        )
    except Exception as e:
        logger.exception("PDF build failed for %s", doc_id)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")
    filename = f"{doc.get('doc_number','document').replace('/','_')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, request: Request):
    user = await get_current_user(request, db)
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.get("status") == "signed" and user.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only admins can delete signed documents")
    await db.documents.delete_one({"id": doc_id})
    return {"message": "deleted"}


# Convenience: list documents per deal (used in deal detail panel)
@router.get("/deals/{deal_id}/documents")
async def list_deal_documents(deal_id: str, request: Request):
    await get_current_user(request, db)
    items = await db.documents.find({"deal_id": deal_id}, {"_id": 0, "content": 0}).sort("created_at", -1).to_list(50)
    return {"data": items}
