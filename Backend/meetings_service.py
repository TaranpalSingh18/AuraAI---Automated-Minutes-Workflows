import sys
import os
from pathlib import Path
import time

# Add Model directory to path to import tasks.py
backend_dir = Path(__file__).parent
model_dir = backend_dir.parent / "Model"
sys.path.insert(0, str(model_dir))

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import Docx2txtLoader
from langchain_google_genai import ChatGoogleGenerativeAI
import json
import ast
import re
import tempfile

# Import functions from Model/tasks.py
try:
    import tasks as model_tasks
except ImportError:
    # Fallback if import fails
    model_tasks = None


def process_transcript_with_gemini(file_content: bytes, gemini_api_key: str):
    """
    Process transcript document using existing AI functions from Model/tasks.py
    Returns: summary, participants list, action items, transcript text
    """
    if not gemini_api_key:
        raise ValueError("Gemini API key is required")
    
    # Trim whitespace from API key
    gemini_api_key = gemini_api_key.strip()
    
    if not gemini_api_key:
        raise ValueError("Gemini API key is required")
    
    # Save uploaded file temporarily to disk
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
        temp_file.write(file_content)
        temp_path = temp_file.name
    
    try:
        # Load document (same as Model/tasks.py)
        doc = Docx2txtLoader(temp_path)
        load_documents = doc.load()
        splitted_docs = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        final_docs = splitted_docs.split_documents(load_documents)
        
        transcript_text = "\n\n".join(d.page_content for d in final_docs)
        
        # Initialize LLM with gemini-2.5-flash (same as Model/tasks.py)
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=gemini_api_key)
        
        # Temporarily replace the global llm in tasks module to use our custom API key
        # This ensures the functions from Model/tasks.py use the correct API key
        original_llm = None
        if model_tasks:
            original_llm = getattr(model_tasks, 'llm', None)
            model_tasks.llm = llm
        
        try:
            # Use the actual functions from Model/tasks.py EXACTLY as they are
            if model_tasks:
                # Get summary - get_result takes final_docs (list of Document objects)
                summary = model_tasks.get_result(final_docs)
                
                # Small delay to avoid hitting rate limits too quickly
                time.sleep(1)
                
                # Get participants using actual function from Model/tasks.py
                participants_raw = model_tasks.get_particpants_names(summary)
                participants = parse_participants(participants_raw)
                
                # Small delay before getting tasks
                time.sleep(1)
                
                # Get action items for each participant using actual function from Model/tasks.py
                action_items = []
                for participant in participants:
                    tasks_raw = model_tasks.get_task(summary, participant)
                    tasks = parse_tasks(tasks_raw, participant)
                    action_items.extend(tasks)
                    # Small delay between participant tasks to avoid rate limits
                    time.sleep(0.5)
            else:
                # Fallback to local implementations
                summary = get_result(llm, final_docs, transcript_text)
                participants_raw = get_participants_names(llm, summary)
                participants = parse_participants(participants_raw)
                action_items = []
                for participant in participants:
                    tasks_raw = get_task(llm, summary, participant)
                    tasks = parse_tasks(tasks_raw, participant)
                    action_items.extend(tasks)
        finally:
            # Restore original llm if it existed
            if model_tasks and original_llm is not None:
                model_tasks.llm = original_llm
        
        return {
            "summary": summary,
            "participants": participants,
            "action_items": action_items,
            "transcript_text": transcript_text
        }
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


def get_result_wrapper(llm, final_docs, transcript_text: str):
    """Wrapper to adapt get_result signature from Model/tasks.py"""
    # The original get_result takes final_docs, but uses transcript_text in prompt
    # We'll create a modified version that works with our setup
    prompt = f"""
    You are the expert of summarizing the whole document in one go and then help each of the particpant to let them know what work has been assigned to them. 
    Like first focus of you is always on summarisation of the whole transcript. You scan the document from A-Z and then let them what's goping on in a good enough paragraph
    (depends upon the size of the transcript). The format of the Transcription should always be

    (TITLE)
    First give the most appropiate title to the transcipt
    
    Particpants of the meet: (Name all the personalities present in the meet)

    Next start describing about the motivation of the meet (mainly describes the main objective of the meet)

    Next explain each thing that has been dicussed in the meet. How;s the work currently going on, and what issues are they currenly facing (if any)

    Next find out what task has been discussed that needs to be done. 

    and at last...Give the conclusion of the whole meet under the heading Conclusion
    (Conclusion)

    So you are given the transcript as {transcript_text}. I need the transcript only in the above format only. If not given I will switch to OpenAI. So you better give
    what i need. 
    """
    
    response = llm.invoke(prompt)
    return response.content


# Fallback functions (same logic as Model/tasks.py)
def get_result(llm, final_docs, transcript_text: str):
    """Generate meeting summary (same logic as Model/tasks.py)"""
    return get_result_wrapper(llm, final_docs, transcript_text)


def get_participants_names(llm, transcript: str):
    """Extract participants list (same logic as Model/tasks.py)"""
    prompt = f"""
        You are a participants listing expert. The main aim of your existence here is to extract the names of the particpants who have attended the meeting from the transcript: {transcript} and return them in a list format only. I repeat output having commas, backticks, etc format is not acceptible. I need purely a list of participants names which are strings. NOTHING MORE.

        For example: Participant Names: Taran , Garv and Vatsal
        Expected Output: ["Taran", "Garv", "Vatsal"]

        For example: Participant Names: Taran and  Manreet
        Expected Output: ["Taran", "Manreet"]

        Make sure you return a list that is iteratable, NOTHING MORE IS NEEDED.
    """
    
    participant_list = llm.invoke(prompt)
    return participant_list.content


def parse_participants(raw: str):
    """Parse participants list (same logic as Model/tasks.py)"""
    raw = raw.strip()
    participants = None
    
    try:
        participants = json.loads(raw)
    except Exception:
        try:
            participants = ast.literal_eval(raw)
        except Exception:
            cleaned = re.sub(r'^\[|\]$', '', raw)
            cleaned = re.sub(r'\s+and\s+', ',', cleaned) 
            parts = [p.strip().strip('"').strip("'") for p in cleaned.split(',') if p.strip()]
            participants = parts
    
    if isinstance(participants, str):
        participants = [participants]
    
    return participants if participants else []


def get_task(llm, transcript: str, person_name: str):
    """Extract tasks for a specific person (same logic as Model/tasks.py)"""
    prompt = f"""
    You are an expert in task determination of a particular person:{person_name} from the transcript:{transcript}. The main aim of your existence is to extract
    the tasks assigned to that person only. You have a characterstic that you dont give vague tasks. Your outputs are well strcutured and are mainly seperated by /n only.
    You are only allowed to give the output in the below format only:
    Example of Output: 
    Task-1 Mention the task clearly (no vaguely defined task), Assigned by: mention the name of the person which has assigned the task
    Task-2 Mention the task clearly (no vaguely defined task). Assigned by: mention the name of the person which has assigned the task
    .
    .
    .
    .
    (upto how many task has been assigned to that person)
    """
    
    result = llm.invoke(prompt)
    return result.content


def parse_tasks(tasks_raw: str, assignee: str):
    """Parse tasks and convert to action items format"""
    action_items = []
    task_lines = [line.strip() for line in tasks_raw.split('\n') if line.strip() and 'Task-' in line]
    
    for task_line in task_lines:
        # Extract task text and assigner
        parts = task_line.split('Assigned by:')
        task_text = parts[0] if parts else task_line
        # Remove Task-X prefix
        task_text = re.sub(r'^Task-\d+\s*', '', task_text).strip()
        task_text = task_text.rstrip(',').strip()
        assigner = parts[1].strip() if len(parts) > 1 else None
        
        if task_text:
            action_items.append({
                "text": task_text,
                "assignee": assignee,
                "assigned_by": assigner or "Unknown"
            })
    
    return action_items

