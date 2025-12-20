"""
Trans2Actions API routes - RAG-based Q&A on meeting transcripts
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime
from typing import List, Optional, Dict, Any

from auth.auth_routes import get_current_user
from trans2action.rag_service import RAGService
from trans2action.file_processor import FileProcessor

router = APIRouter(prefix="/trans2actions", tags=["trans2actions"])
security = HTTPBearer()

# Database will be set from main.py
database = None

def set_database(db):
    global database
    database = db


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class QueryRequest(BaseModel):
    query: str
    workspace_id: Optional[str] = None
    conversation_history: Optional[List[Message]] = None


class QueryResponse(BaseModel):
    answer: str
    query: str


class UploadFileResponse(BaseModel):
    success: bool
    message: str
    document_id: Optional[str] = None
    filename: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
async def query_transcripts(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Query meeting transcripts using RAG (Retrieval-Augmented Generation)
    
    Basic RAG Implementation:
    1. Retrieval: Fetches relevant transcript chunks from uploaded documents/meetings
    2. Augmentation: Combines retrieved context with user query
    3. Generation: Uses LLM to generate answer based on context
    
    Works for both Admin and Employee users:
    - Admin: Can query all transcripts they've uploaded
    - Employee: Can query transcripts from their workspace
    
    Users can ask questions about their meetings and get answers based on transcript content
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Get user settings (Gemini API key)
    user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
    gemini_api_key = user.get("settings", {}).get("gemini_api_key", "").strip()
    
    if not gemini_api_key:
        raise HTTPException(
            status_code=400,
            detail="Gemini API key not configured. Please add it in Settings."
        )
    
    # Determine workspace filter
    workspace_filter = {}
    if request.workspace_id:
        workspace_filter["workspace_id"] = request.workspace_id
    elif current_user.get("persona") == "employee":
        # Employees see only their workspace meetings
        user_workspace = user.get("settings", {}).get("workspace_id")
        if user_workspace:
            workspace_filter["workspace_id"] = user_workspace
        else:
            # Employee without workspace - return empty
            raise HTTPException(
                status_code=400,
                detail="No workspace configured. Please configure workspace ID in Settings."
            )
    
    # Fetch relevant transcripts from database
    # Prioritize uploaded documents over meeting transcripts for Trans2Actions queries
    transcripts = []
    transcript_metadata = []  # Track which document each transcript comes from
    
    # First, fetch uploaded documents (these are more relevant for Trans2Actions)
    doc_query = {"uploaded_by": current_user["id"]}
    if workspace_filter.get("workspace_id"):
        doc_query["workspace_id"] = workspace_filter["workspace_id"]
    
    # Sort by most recent first to prioritize latest uploads
    documents_cursor = database.trans2actions_documents.find(doc_query).sort("created_at", -1)
    async for doc in documents_cursor:
        doc_content = doc.get("content", "")
        if doc_content:
            transcripts.append(doc_content)
            transcript_metadata.append({
                "type": "document",
                "filename": doc.get("filename", "Unknown"),
                "id": str(doc.get("_id", "")),
                "created_at": doc.get("created_at")
            })
    
    # Only fetch meeting transcripts if NO documents were found
    # For Trans2Actions, we prioritize uploaded documents exclusively
    if not transcripts:
        meetings_cursor = database.meetings.find(workspace_filter)
        async for meeting in meetings_cursor:
            transcript_text = meeting.get("transcript_text", "")
            if transcript_text:
                transcripts.append(transcript_text)
                transcript_metadata.append({
                    "type": "meeting",
                    "title": meeting.get("title", "Unknown Meeting"),
                    "id": str(meeting.get("_id", "")),
                    "created_at": meeting.get("created_at")
                })
    
    if not transcripts:
        return QueryResponse(
            answer="No documents or meeting transcripts found. Please upload documents or meeting transcripts first.",
            query=request.query
        )
    
    # Get conversation history from database or use provided history
    conversation_history = request.conversation_history or []
    
    # Load conversation history from database if not provided
    if not conversation_history:
        conversation_doc = await database.conversations.find_one({
            "user_id": current_user["id"],
            "product": "Trans2Actions"
        })
        if conversation_doc:
            conversation_history = [
                Message(role=msg["role"], content=msg["content"])
                for msg in conversation_doc.get("messages", [])
            ]
    
    # Convert conversation_history to list of dicts for RAG service
    # This handles both Pydantic Message objects and dicts
    conversation_history_dicts = []
    for msg in conversation_history:
        if isinstance(msg, dict):
            conversation_history_dicts.append(msg)
        else:
            # Pydantic Message object
            conversation_history_dicts.append({
                "role": getattr(msg, "role", "user"),
                "content": getattr(msg, "content", "")
            })
    
    # Initialize RAG service and query with conversation history
    try:
        rag_service = RAGService(gemini_api_key=gemini_api_key)
        # Pass metadata to help prioritize recent documents
        answer = rag_service.query_transcripts_with_history(
            request.query, 
            transcripts, 
            conversation_history_dicts,
            transcript_metadata=transcript_metadata if 'transcript_metadata' in locals() else []
        )
        
        # Save messages to database
        # Prepare messages for storage (current + new exchange)
        # Use conversation_history_dicts which is already converted to dicts
        messages_to_save = conversation_history_dicts.copy()
        messages_to_save.append({"role": "user", "content": request.query})
        messages_to_save.append({"role": "assistant", "content": answer})
        
        # Update or create conversation document
        await database.conversations.update_one(
            {
                "user_id": current_user["id"],
                "product": "Trans2Actions"
            },
            {
                "$set": {
                    "messages": messages_to_save,
                    "updated_at": datetime.utcnow()
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        
        return QueryResponse(
            answer=answer,
            query=request.query
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


@router.post("/upload", response_model=UploadFileResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a document (PDF, TXT, DOCX) for use in Trans2Actions RAG
    """
    # Check file type
    if not FileProcessor.is_supported(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported formats: PDF, TXT, DOCX"
        )
    
    # Read file content
    file_content = await file.read()
    
    # Extract text from file
    extracted_text = FileProcessor.extract_text_from_file(file_content, file.filename)
    
    if not extracted_text:
        raise HTTPException(
            status_code=400,
            detail="Failed to extract text from file. The file may be corrupted or empty."
        )
    
    # Get user settings
    user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
    user_workspace = user.get("settings", {}).get("workspace_id") if current_user.get("persona") == "employee" else None
    
    # Store document in database
    try:
        document_data = {
            "filename": file.filename,
            "content": extracted_text,
            "uploaded_by": current_user["id"],
            "workspace_id": user_workspace,
            "created_at": datetime.utcnow(),
            "file_size": len(file_content)
        }
        
        result = await database.trans2actions_documents.insert_one(document_data)
        document_id = str(result.inserted_id)
        
        return UploadFileResponse(
            success=True,
            message=f"Document '{file.filename}' uploaded successfully and is now available for queries.",
            document_id=document_id,
            filename=file.filename
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving document: {str(e)}"
        )


@router.get("/documents")
async def list_documents(
    current_user: dict = Depends(get_current_user)
):
    """
    List all uploaded documents for the current user
    """
    user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
    user_workspace = user.get("settings", {}).get("workspace_id") if current_user.get("persona") == "employee" else None
    
    # Build query filter
    query = {"uploaded_by": current_user["id"]}
    if user_workspace:
        query["workspace_id"] = user_workspace
    
    documents = []
    async for doc in database.trans2actions_documents.find(query).sort("created_at", -1):
        documents.append({
            "id": str(doc["_id"]),
            "filename": doc.get("filename", "Unknown"),
            "created_at": doc.get("created_at", datetime.utcnow()).isoformat(),
            "file_size": doc.get("file_size", 0)
        })
    
    return {"documents": documents}


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an uploaded document
    """
    try:
        doc_object_id = ObjectId(document_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid document ID")
    
    # Check if document belongs to user
    doc = await database.trans2actions_documents.find_one({"_id": doc_object_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.get("uploaded_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="You don't have permission to delete this document")
    
    # Delete document
    await database.trans2actions_documents.delete_one({"_id": doc_object_id})
    
    return {"success": True, "message": "Document deleted successfully"}

