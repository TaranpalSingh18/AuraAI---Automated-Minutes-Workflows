"""
RAG service for Trans2Actions - uses meeting transcripts as knowledge base
"""
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.documents import Document

# Add Model directory to path
backend_dir = Path(__file__).parent.parent
model_dir = backend_dir.parent / "Model"
sys.path.insert(0, str(model_dir))


class RAGService:
    """RAG service for querying meeting transcripts"""
    
    def __init__(self, gemini_api_key: str):
        if not gemini_api_key:
            raise ValueError("Gemini API key is required")
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=gemini_api_key)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def create_context_from_transcripts(
        self, 
        transcripts: List[str], 
        query: Optional[str] = None,
        transcript_metadata: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Create a context string from multiple transcripts
        Uses basic RAG: splits transcripts into chunks and prioritizes most recent documents
        """
        if not transcripts:
            return ""
        
        # If we have metadata, prioritize most recent documents
        if transcript_metadata and len(transcript_metadata) == len(transcripts):
            # Sort transcripts by creation date (most recent first)
            indexed_transcripts = list(zip(transcripts, transcript_metadata))
            
            def get_sort_key(x):
                metadata = x[1]
                created_at = metadata.get("created_at")
                if created_at is None:
                    return datetime.min
                if isinstance(created_at, datetime):
                    return created_at
                # Try to parse if it's a string
                try:
                    if isinstance(created_at, str):
                        return datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    pass
                return datetime.min
            
            indexed_transcripts.sort(key=get_sort_key, reverse=True)
            
            # Filter to only use documents (not meetings) if documents exist
            document_transcripts = [t for t in indexed_transcripts if t[1].get("type") == "document"]
            meeting_transcripts = [t for t in indexed_transcripts if t[1].get("type") == "meeting"]
            
            # Prioritize: Use ONLY documents if available, otherwise use meetings
            if document_transcripts:
                # Use only the most recent document for focused answers
                prioritized_data = document_transcripts[:1]
            else:
                # Fallback to meetings if no documents
                prioritized_data = meeting_transcripts[:2]
            
            # Update both transcripts and metadata to match
            transcripts = [t[0] for t in prioritized_data]
            transcript_metadata = [t[1] for t in prioritized_data]
        
        # Process each transcript separately to maintain document boundaries
        all_chunks = []
        for i, transcript in enumerate(transcripts):
            # Split each transcript into chunks
            chunks = self.text_splitter.split_text(transcript)
            # Add document identifier to chunks with filename if available
            if transcript_metadata and i < len(transcript_metadata):
                meta = transcript_metadata[i]
                filename = meta.get("filename", f"Document {i+1}")
                doc_label = f"[Document: {filename}]"
            else:
                doc_label = f"[Content {i+1}]"
            labeled_chunks = [f"{doc_label}\n{chunk}" for chunk in chunks]
            all_chunks.extend(labeled_chunks)
        
        # Basic RAG: prioritize chunks from most recent documents
        # Limit total length to avoid token limits, but ensure we get enough content
        max_total_length = 12000  # Increased to get more content from the document
        
        selected_chunks = []
        total_length = 0
        
        # Take chunks in order (most recent documents first)
        for chunk in all_chunks:
            chunk_length = len(chunk)
            if total_length + chunk_length > max_total_length:
                break
            selected_chunks.append(chunk)
            total_length += chunk_length
        
        context = "\n\n---CHUNK SEPARATOR---\n\n".join(selected_chunks)
        return context
    
    def query_transcripts(self, query: str, transcripts: List[str]) -> str:
        """
        Query transcripts using RAG approach (without conversation history)
        Basic RAG implementation: retrieve relevant context and generate answer
        
        Args:
            query: User's question
            transcripts: List of transcript texts to search
            
        Returns:
            Answer based on transcript context
        """
        if not transcripts:
            return "No transcripts available. Please upload meeting transcripts first."
        
        # Create context from transcripts (basic RAG retrieval)
        context = self.create_context_from_transcripts(transcripts, query)
        
        if not context:
            return "No relevant context found in the transcripts. Please ensure transcripts are properly uploaded."
        
        # Build prompt for RAG (basic RAG generation)
        prompt = f"""You are an AI assistant helping users understand their meeting transcripts and project context.

Here is the context retrieved from meeting transcripts:

{context}

Based ONLY on the above transcript context, answer the following question accurately and concisely. 
- If the answer can be found in the transcripts, provide it clearly.
- If the answer cannot be found in the transcripts, say "I cannot find this information in the uploaded transcripts."
- Do not make up information that is not in the transcripts.

Question: {query}

Answer:"""
        
        # Get response from LLM (RAG generation step)
        try:
            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def query_transcripts_with_history(
        self, 
        query: str, 
        transcripts: List[str],
        conversation_history: List[Any],
        transcript_metadata: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Query transcripts using RAG approach with conversation history
        
        Args:
            query: User's question
            transcripts: List of transcript texts to search
            conversation_history: List of previous messages (can be dict or Pydantic Message objects)
            
        Returns:
            Answer based on transcript context and conversation history
        """
        if not transcripts:
            return "No transcripts available. Please upload meeting transcripts first."
        
        # Create context from transcripts (basic RAG retrieval)
        context = self.create_context_from_transcripts(transcripts, query, transcript_metadata)
        
        if not context:
            return "No relevant context found in the transcripts. Please ensure transcripts are properly uploaded."
        
        # Build conversation history string
        history_text = ""
        if conversation_history:
            history_parts = []
            for msg in conversation_history[-5:]:  # Include last 5 exchanges for context
                # Handle both dict and Pydantic Message objects
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                else:
                    # Pydantic model or object with attributes
                    role = getattr(msg, "role", "user")
                    content = getattr(msg, "content", "")
                
                role_display = "User" if role == "user" else "Assistant"
                if content:  # Only add non-empty messages
                    history_parts.append(f"{role_display}: {content}")
            history_text = "\n\n".join(history_parts)
        
        # Build prompt for RAG with conversation history (basic RAG generation)
        if history_text:
            prompt = f"""You are an AI assistant helping users understand their uploaded documents and meeting transcripts.

Here is the context retrieved from the uploaded documents (most recent documents are prioritized):

{context}

Previous conversation:
{history_text}

Based ONLY on the above document context and conversation history, answer the following question accurately and concisely.
- Focus on information from the most recent documents first (marked as [Document 1], [Document 2], etc.).
- If the answer can be found in the documents, provide it clearly.
- If the answer cannot be found in the documents, say "I cannot find this information in the uploaded documents."
- Maintain context from the previous conversation.
- Do not make up information that is not in the documents.
- Do not use information from older documents if it conflicts with recent documents.

Question: {query}

Answer:"""
        else:
            prompt = f"""You are an AI assistant helping users understand their uploaded documents and meeting transcripts.

Here is the context retrieved from the uploaded documents (most recent documents are prioritized):

{context}

Based ONLY on the above document context, answer the following question accurately and concisely.
- Focus on information from the most recent documents first (marked as [Document 1], [Document 2], etc.).
- If the answer can be found in the documents, provide it clearly.
- If the answer cannot be found in the documents, say "I cannot find this information in the uploaded documents."
- Do not make up information that is not in the documents.
- Do not use information from older documents if it conflicts with recent documents.

Question: {query}

Answer:"""
        
        # Get response from LLM (RAG generation step)
        try:
            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Error generating response: {str(e)}"


# Database will be set from main.py
database = None

def set_database(db):
    global database
    database = db

