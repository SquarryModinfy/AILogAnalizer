"""
Класс для работы с векторной базой данных
"""

import os
import json
import numpy as np
import torch
import faiss
from transformers import AutoTokenizer, AutoModel
from core.constants import logger

class Vectorizer:
    def __init__(self):
        logger.debug("Инициализация Vectorizer")
        self.tokenizer = AutoTokenizer.from_pretrained("microsoft/MiniLM-L12-H384-uncased")
        self.model = AutoModel.from_pretrained("microsoft/MiniLM-L12-H384-uncased")
        self.dimension = 384
        self.index = None
        self.metadata = []
        self.db_path = "./vector_db"
        self._init_db()
        logger.debug("Vectorizer инициализирован")
    
    def _init_db(self):
        try:
            logger.debug("Инициализация базы данных")
            os.makedirs(self.db_path, exist_ok=True)
            
            self.index = faiss.IndexFlatL2(self.dimension)
            
            metadata_path = os.path.join(self.db_path, "metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            
            logger.debug(f"База данных инициализирована. Количество записей: {len(self.metadata)}")
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}", exc_info=True)
            raise
    
    def get_embeddings(self, text):
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1)
        
        return embeddings[0].numpy().astype(np.float64)
    
    def add_to_db(self, text):
        try:
            embeddings = self.get_embeddings(text)
            
            self.index.add(np.array([embeddings], dtype=np.float64))
            
            self.metadata.append(text)
            
            metadata_path = os.path.join(self.db_path, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            
            index_path = os.path.join(self.db_path, "faiss.index")
            faiss.write_index(self.index, index_path)
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении в базу данных: {e}")
            return False
    
    def search(self, query_embeddings, k=5):
        try:
            distances, indices = self.index.search(np.array([query_embeddings], dtype=np.float64), k)
            
            results = []
            for idx in indices[0]:
                if idx < len(self.metadata):
                    results.append(self.metadata[idx])
            
            return "\n".join(results)
        except Exception as e:
            logger.error(f"Ошибка при поиске: {e}")
            return ""
    
    def clear_db(self):
        try:
            self.index = faiss.IndexFlatL2(self.dimension)
            
            self.metadata = []
            
            metadata_path = os.path.join(self.db_path, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            
            index_path = os.path.join(self.db_path, "faiss.index")
            faiss.write_index(self.index, index_path)
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при очистке базы данных: {e}")
            return False
    
    def get_stats(self):
        try:
            return {
                "total_records": len(self.metadata),
                "dimension": self.dimension,
                "directory": self.db_path
            }
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return None 