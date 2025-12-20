"""
File processor for Trans2Actions - extracts text from various file formats
"""
from typing import Optional
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
import tempfile
import os


class FileProcessor:
    """Process uploaded files and extract text"""
    
    SUPPORTED_EXTENSIONS = {
        '.pdf': 'pdf',
        '.txt': 'txt',
        '.docx': 'docx',
        '.doc': 'docx',  # Will try to process as docx
    }
    
    @staticmethod
    def extract_text_from_file(file_content: bytes, filename: str) -> Optional[str]:
        """
        Extract text from uploaded file
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            
        Returns:
            Extracted text or None if unsupported format
        """
        if not filename:
            return None
        
        # Get file extension
        ext = os.path.splitext(filename.lower())[1]
        
        if ext not in FileProcessor.SUPPORTED_EXTENSIONS:
            return None
        
        file_type = FileProcessor.SUPPORTED_EXTENSIONS[ext]
        
        try:
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
                temp_file.write(file_content)
                temp_path = temp_file.name
            
            try:
                if file_type == 'pdf':
                    # Use PyPDFLoader from LangChain
                    loader = PyPDFLoader(temp_path)
                    documents = loader.load()
                    text = "\n\n".join([doc.page_content for doc in documents])
                
                elif file_type == 'txt':
                    # Use TextLoader from LangChain
                    loader = TextLoader(temp_path, encoding='utf-8')
                    documents = loader.load()
                    text = documents[0].page_content if documents else ""
                
                elif file_type == 'docx':
                    # Use Docx2txtLoader from LangChain
                    loader = Docx2txtLoader(temp_path)
                    documents = loader.load()
                    text = "\n\n".join([doc.page_content for doc in documents])
                
                else:
                    return None
                
                return text.strip()
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            print(f"Error processing file {filename}: {e}")
            return None
    
    @staticmethod
    def is_supported(filename: str) -> bool:
        """Check if file format is supported"""
        if not filename:
            return False
        ext = os.path.splitext(filename.lower())[1]
        return ext in FileProcessor.SUPPORTED_EXTENSIONS

