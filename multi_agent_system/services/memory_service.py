import os
import sys
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from datetime import datetime
import uuid

# 确保能导入 utils 目录下的 volc_clients
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from utils.volc_clients import EmbeddingClient
from ..core.models.memory import Memory, MemoryQuery

class MemoryService:
    """
    记忆服务基础设施。
    基于 ChromaDB (本地持久化) 和火山引擎 Embedding 实现。
    """

    def __init__(self, persist_directory: str = "./storage/memory"):
        self.persist_directory = persist_directory
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # 1. 初始化 ChromaDB 本地客户端
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
        # 2. 初始化 Embedding 客户端
        self.embedding_client = EmbeddingClient()
        
        # 3. 存储已创建的集合 (Collection) 引用
        self.collections = {}

    def _get_collection(self, namespace: str):
        """
        获取或创建指定命名空间的集合。
        """
        if namespace not in self.collections:
            # 获取或创建集合，这里不指定默认的 embedding_function，我们手动处理
            self.collections[namespace] = self.client.get_or_create_collection(name=namespace)
        return self.collections[namespace]

    async def add_memory(self, memory: Memory):
        """
        新增一条记忆。
        """
        print(f"[MemoryService] Adding memory to '{memory.namespace}': {memory.content[:50]}...")
        
        collection = self._get_collection(memory.namespace)
        
        # 1. 获取文本的向量
        vector = self.embedding_client.get_embedding(memory.content)
        if not vector:
            print("[MemoryService] Failed to get embedding for memory content.")
            return False
            
        # 2. 写入 ChromaDB
        collection.add(
            ids=[memory.memory_id],
            embeddings=[vector],
            documents=[memory.content],
            metadatas=[{
                **memory.metadata,
                "created_at": memory.created_at.isoformat()
            }]
        )
        return True

    async def search(self, query: MemoryQuery) -> List[Memory]:
        """
        语义检索最相关的记忆。
        """
        print(f"[MemoryService] Searching memory in '{query.namespace}' for: {query.query_text}")
        
        collection = self._get_collection(query.namespace)
        
        # 1. 将查询文本向量化
        query_vector = self.embedding_client.get_embedding(query.query_text)
        if not query_vector:
            return []
            
        # 2. 执行向量检索
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=query.top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        # 3. 封装为 Memory 对象列表
        memories = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                # 过滤低分结果 (ChromaDB 的 distance 越小代表越相似，通常需要按需调整阈值)
                distance = results["distances"][0][i]
                # 这里可以根据具体距离算法转换成 score，暂时直接使用
                
                memories.append(Memory(
                    memory_id=results["ids"][0][i],
                    namespace=query.namespace,
                    content=results["documents"][0][i],
                    metadata=results["metadatas"][0][i],
                    created_at=datetime.fromisoformat(results["metadatas"][0][i].get("created_at", datetime.utcnow().isoformat()))
                ))
        
        return memories

# 实例化全局服务单例
memory_service = MemoryService()
