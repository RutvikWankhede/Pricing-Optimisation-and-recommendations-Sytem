import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.database.models import Report, User
from app.services.reporting import generate_excel_report, generate_pdf_report
from app.api.routes.auth import get_current_user

router = APIRouter(prefix="/reports", tags=["Export Services"])

@router.post("/generate")
def generate_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger generation of both PDF and Excel intelligence reports."""
    from app.database.models import SalesData
    if db.query(SalesData).count() == 0:
        raise HTTPException(
            status_code=400,
            detail="No transaction ledger exists. Please upload a dataset in the Ingestion Center first."
        )
        
    try:
        excel_path = generate_excel_report(db, current_user.id)
        pdf_path = generate_pdf_report(db, current_user.id)
        
        return {
            "status": "success",
            "message": "Reports successfully generated.",
            "excel_file": os.path.basename(excel_path),
            "pdf_file": os.path.basename(pdf_path)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate reports: {str(e)}"
        )

@router.get("/download/excel")
def download_excel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download the latest generated Excel report."""
    report = db.query(Report)\
               .filter(Report.report_type == "excel")\
               .order_by(Report.created_at.desc())\
               .first()
               
    if not report or not os.path.exists(report.file_path):
        # Try generating on the fly
        try:
            path = generate_excel_report(db, current_user.id)
            return FileResponse(
                path,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=os.path.basename(path)
            )
        except Exception:
            raise HTTPException(status_code=404, detail="Excel report not found. Please generate reports first.")
            
    return FileResponse(
        report.file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(report.file_path)
    )

@router.get("/download/pdf")
def download_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download the latest generated PDF executive report."""
    report = db.query(Report)\
               .filter(Report.report_type == "pdf")\
               .order_by(Report.created_at.desc())\
               .first()
               
    if not report or not os.path.exists(report.file_path):
        # Try generating on the fly
        try:
            path = generate_pdf_report(db, current_user.id)
            return FileResponse(
                path,
                media_type="application/pdf",
                filename=os.path.basename(path)
            )
        except Exception:
            raise HTTPException(status_code=404, detail="PDF report not found. Please generate reports first.")
            
    return FileResponse(
        report.file_path,
        media_type="application/pdf",
        filename=os.path.basename(report.file_path)
    )
