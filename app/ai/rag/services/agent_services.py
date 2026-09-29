import os
import hashlib
from dotenv import load_dotenv
import asyncio
from llama_index.core import VectorStoreIndex, Settings, SimpleDirectoryReader
from llama_index.core.ingestion import IngestionPipeline
from llama_index.llms.groq import Groq
from pinecone import Pinecone
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.pinecone import PineconeVectorStore
from fastapi import UploadFile
import gc

load_dotenv()

embed_model = HuggingFaceEmbedding(
    model_name='intfloat/multilingual-e5-small'
)

groq_key = os.getenv('GROQ_API_KEY')
llm = Groq(
    model='llama-3.1-8b-instant',
    api_key=groq_key,
    temperature = 0.2,
)

INDEX_NAME = 'supportflow-knowledge'
Settings.llm = llm
Settings.embed_model = embed_model
Settings.chunk_size = 512
Settings.chunk_overlap = 64


def get_index(organization_id:str):
    
    pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
    
    pinecone_index = pc.Index(INDEX_NAME)
    
    vectore_store = PineconeVectorStore(pinecone_index=pinecone_index, namespace=f'org_{organization_id}')
    
    index = VectorStoreIndex.from_vector_store(vector_store=vectore_store)
    
    return index


async def proccess_and_upload_file(file: UploadFile, organization_id:str):
    upload_dir='../../data'
    
    os.makedirs(upload_dir, exist_ok=True)
    
    namespace= f'org_{organization_id}'
    
    file_path = os.path.join(upload_dir, file.filename)
    
    pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
            
    pinecone_index = pc.Index(INDEX_NAME)
    
    
    
    
    try:
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()
        
        with open(file_path, 'wb') as buffer:
            buffer.write(content)
            
        documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
        
        
        index = get_index(organization_id)
        
        pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(
                    chunk_size=Settings.chunk_size,
                    chunk_overlap=Settings.chunk_overlap
                )
            ],
           
        )
        
        proccesse_nodes = pipeline.run(documents= documents, show_progress=True, num_workers=1)
        
        index.insert_nodes(proccesse_nodes)
        
        gc.collect()
        
        return len(proccesse_nodes)
    
    except Exception as e:
        print(f'Error ene el servicio al procesar archivo: {e}')
        
        raise e
    
    finally:
        
        if os.path.exists(file_path):
            os.remove(file_path)