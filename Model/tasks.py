import docx2txt
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import Docx2txtLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os


import json
import ast
import re

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")

# Initialize llm only when needed (for function imports)
llm = None
if gemini_api_key:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=gemini_api_key)


def get_result(final_docs):
    prompt =f"""
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

    So you are given the transcript as {final_docs}. I need the transcript only in the above format only. If not given I will switch to OpenAI. So you better give
    what i need. 
    """

    response = llm.invoke(prompt)
    transcript = response.content
    return transcript

def get_particpants_names(transcript: str):
    prompt = f"""
        You are a participants listing expert. The main aim of your existence here is to extract the names of the particpants who have attended the meeting from the transcript: {transcript} and return them in a list format only. I repeat output having commas, backticks, etc format is not acceptible. I need purely a list of participants names which are strings. NOTHING MORE.

        For example: Participant Names: Taran , Garv and Vatsal
        Expected Output: ["Taran", "Garv", "Vatsal"]

        For example: Participant Names: Taran and  Manreet
        Expected Output: ["Taran", "Manreet"]

        Make sure you return a list that is iteratable, NOTHING MORE IS NEEDED.
            """

    particant_list = llm.invoke(prompt)
    return particant_list.content


def get_task(transcript: str, person_name: str):
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


# Only run when script is executed directly, not when imported
if __name__ == "__main__":
    # Initialize llm for direct script execution
    if not llm and gemini_api_key:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=gemini_api_key)
    
    # Load document only when running as script
    doc = Docx2txtLoader("transcript.docx")
    load_documents = doc.load()
    splitted_docs = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    final_docs = splitted_docs.split_documents(load_documents)
    
    transcript_text = "\n\n".join(d.page_content for d in final_docs)
    
    answer = get_result(final_docs)  
    print(answer)

    list_parti = get_particpants_names(answer)

    raw = list_parti.strip()

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

    print(participants)

    for i in participants:
        task_assigned = get_task(answer, i)
        print(task_assigned)
