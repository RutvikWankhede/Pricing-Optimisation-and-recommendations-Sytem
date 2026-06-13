import io
import uuid
import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.db import get_db, SessionLocal
from app.database.models import Dataset, User
from app.database.schemas import DatasetResponse
from app.services.data_cleaning import process_uploaded_file, map_columns
from app.services.cloud_storage import upload_file
from app.services.elasticity import calculate_all_elasticities
from app.services.forecasting import train_and_forecast_all
from app.services.recommendation import generate_all_recommendations
from app.api.routes.auth import get_current_user
from app.core.config import settings
from fastapi import Request
from app.core.limiter import limiter
import logging
logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/upload", tags=["Dataset Upload"])

class IngestRequest(BaseModel):
    dataset_id: str
    mappings: dict

def run_analytics_pipeline(db_session_factory, file_path: str, file_name: str, dataset_id: str, mappings: dict = None):
    """Run data cleaning, training, and analytics forecasting in background."""
    db = db_session_factory()
    try:
        from app.database.models import SalesData, Product, Dataset, ForecastingResult, ElasticityAnalysis, PricingRecommendation, ScenarioSimulation, Report
        
        # Purge all old data and intermediate calculations
        db.query(ForecastingResult).delete()
        db.query(ElasticityAnalysis).delete()
        db.query(PricingRecommendation).delete()
        db.query(ScenarioSimulation).delete()
        db.query(SalesData).delete()
        db.query(Product).delete()
        db.query(Dataset).filter(Dataset.id != dataset_id).delete()
        db.commit()

        with open(file_path, "rb") as f:
            file_content = f.read()
        # 1. Clean and insert sales records
        process_uploaded_file(db, file_content, file_name, dataset_id, mappings)
        
        # 2. Re-calculate price elasticities
        calculate_all_elasticities(db)
        
        # 3. Re-train ML models and forecast
        train_and_forecast_all(db)
        
        # 4. Generate recommendations
        generate_all_recommendations(db)
        
        # 5. Pipeline success: set status to processed
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset:
            dataset.status = "processed"
            db.commit()
        
    except Exception as e:
        print(f"Background Pipeline Error: {str(e)}")
        try:
            from app.database.models import Dataset
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if dataset:
                dataset.status = "failed"
                db.commit()
        except Exception as rollback_err:
            print(f"Failed to set status to failed: {str(rollback_err)}")
    finally:
        db.close()

@router.post("/analyze", status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")
async def analyze_dataset(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a dataset file and analyze its headers/sample rows for mapping preview."""
    if not file.filename.endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a CSV or Excel spreadsheet."
        )
        
    # Read file content
    content = await file.read()
    
    # Save a raw copy to disk using dataset_id
    dataset_id = str(uuid.uuid4())
    raw_filename = f"{dataset_id}_{file.filename}"
    raw_path = settings.UPLOAD_FOLDER / raw_filename
    with open(raw_path, "wb") as f:
        f.write(content)
        
    try:
        # Load sample for parsing headers and preview rows
        if file.filename.endswith((".xlsx", ".xls")):
            df_sample = pd.read_excel(io.BytesIO(content), nrows=5)
        else:
            df_sample = pd.read_csv(io.BytesIO(content), nrows=5)
            
        # Extract headers and row records
        headers = list(df_sample.columns)
        # Convert df rows to list of dicts, ensuring NaN values are converted to None for JSON serializability
        preview_rows = df_sample.replace({pd.NA: None, float('nan'): None}).to_dict(orient="records")
        
        # Auto-map columns
        auto_mappings = map_columns(headers)
        
    except Exception as e:
        # If preview parsing fails, delete file and raise error
        if raw_path.exists():
            raw_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to parse file preview: {str(e)}"
        )
        
    # Register dataset in DB as uploaded (pending mapping confirmation)
    dataset = Dataset(
        id=dataset_id,
        file_name=file.filename,
        user_id=current_user.id,
        total_records=0,
        status="uploaded"
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    return {
        "dataset_id": dataset.id,
        "file_name": file.filename,
        "headers": headers,
        "auto_mappings": auto_mappings,
        "preview_rows": preview_rows
    }

@router.post("/ingest", response_model=DatasetResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest_dataset(
    req: IngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm column mapping and trigger background ingestion processing."""
    dataset = db.query(Dataset).filter(Dataset.id == req.dataset_id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
        
    raw_filename = f"{dataset.id}_{dataset.file_name}"
    raw_path = settings.UPLOAD_FOLDER / raw_filename
    
    if not raw_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Raw upload file not found on server disk."
        )
        
    # Update dataset status to show we are queuing it for ingestion
    dataset.status = "processing"
    db.commit()
    db.refresh(dataset)
    
    # Trigger background pipeline
    background_tasks.add_task(
        run_analytics_pipeline,
        SessionLocal,
        str(raw_path),
        dataset.file_name,
        dataset.id,
        req.mappings
    )
    
    return dataset

@router.post("/upload_dataset", response_model=DatasetResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("20/minute")
async def upload_dataset(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Legacy endpoint: Upload sales transactions Excel/CSV file and trigger the analytics pipeline immediately (auto-mapped)."""
    if not file.filename.endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a CSV or Excel spreadsheet."
        )
    content = await file.read()
    if len(content) > settings.MAX_DOCUMENT_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="Uploaded file exceeds maximum allowed size.")
    dataset_id = str(uuid.uuid4())
    raw_filename = f"{dataset_id}_{file.filename}"
    raw_path = settings.UPLOAD_FOLDER / raw_filename
    with open(raw_path, "wb") as f:
        f.write(content)

    # Attempt Cloudinary upload
    try:
        file_url = upload_file(content, raw_filename)
    except Exception as e:
        # Log the failure and continue with local storage only
        logger.error(f"Cloudinary upload failed for {raw_filename}: {e}")
        file_url = None

    dataset = Dataset(
        id=dataset_id,
        file_name=file.filename,
        user_id=current_user.id,
        total_records=0,
        status="uploaded",
        file_url=file_url,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    background_tasks.add_task(
        run_analytics_pipeline,
        SessionLocal,
        str(raw_path),
        dataset.file_name,
        dataset.id,
        None
    )
    return dataset


@router.get("/sample")
def download_sample_file(
    format: str = "csv",
    current_user: User = Depends(get_current_user)
):
    """Download the benchmark pricing optimization sample dataset in CSV or Excel format."""
    sample_csv_path = settings.BASE_DIR / "datasets" / "sample_data" / "sales_sample.csv"
    
    # If the file doesn't exist yet, we trigger the generation
    if not sample_csv_path.exists():
        try:
            from datasets.sample_data.generate_sample import generate_sample_dataset
            generate_sample_dataset()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate sample dataset: {str(e)}"
            )
            
    if format == "excel":
        try:
            df = pd.read_csv(sample_csv_path)
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Sales Sample')
            out.seek(0)
            return StreamingResponse(
                out,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=sales_sample.xlsx"}
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to export Excel file: {str(e)}"
            )
    else:
        return FileResponse(
            str(sample_csv_path),
            media_type="text/csv",
            filename="sales_sample.csv"
        )

@router.post("/demo", response_model=DatasetResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_demo_dataset(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Instantly seed the database with the sample business intelligence demo dataset."""
    sample_csv_path = settings.BASE_DIR / "datasets" / "sample_data" / "sales_sample.csv"
    
    if not sample_csv_path.exists():
        try:
            from datasets.sample_data.generate_sample import generate_sample_dataset
            generate_sample_dataset()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to locate or generate demo dataset: {str(e)}"
            )
            
    # Create dataset record
    dataset_id = str(uuid.uuid4())
    dataset = Dataset(
        id=dataset_id,
        file_name="sales_sample.csv",
        user_id=current_user.id,
        total_records=0,
        status="processing"
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    # Copy file to upload folder so we can reference it
    raw_path = settings.UPLOAD_FOLDER / f"{dataset_id}_sales_sample.csv"
    try:
        with open(sample_csv_path, "rb") as sf:
            content = sf.read()
        with open(raw_path, "wb") as df:
            df.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prepare demo dataset file: {str(e)}"
        )
        
    # Queue background task (mappings = None targets auto mapping)
    background_tasks.add_task(
        run_analytics_pipeline,
        SessionLocal,
        str(raw_path),
        "sales_sample.csv",
        dataset.id,
        None
    )
    
    return dataset

@router.get("/status/{dataset_id}", response_model=DatasetResponse)
def get_upload_status(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve details and processing status of an uploaded dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    return dataset

@router.get("/history", response_model=list[DatasetResponse])
def get_upload_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of all datasets uploaded."""
    return db.query(Dataset).order_by(Dataset.upload_time.desc()).all()

