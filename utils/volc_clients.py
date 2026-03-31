import os
import yaml
from volcenginesdkarkruntime import Ark

# Define default paths based on the current file location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "docs")


class BaseVolcengineClient:
    """
    火山引擎 API 基础客户端。
    负责读取 YAML 配置文件，并初始化基础的 Ark 客户端连接。
    """
    
    def __init__(self, config_file_path: str):
        """
        初始化基础客户端。
        
        Args:
            config_file_path (str): YAML 配置文件（如 API_CZ.yaml 或 API_DR.yaml）的绝对路径。
        """
        self.config_file_path = config_file_path
        self.config = self._load_config()
        
        # 确定请求的 base_url，默认使用开发机环境
        self.base_url = self.config.get("base_url", "https://ark-cn-beijing.bytedance.net/api/v3")
        
        # 初始化 Ark client
        # 子类如果需要使用不同的 API Key（例如 Embedding 使用 EMB_API_KEY），需要在子类中重写此属性
        self.api_key = self.config.get("ARK_API_KEY")
        self.client = Ark(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def _load_config(self) -> dict:
        """读取并解析指定的 YAML 配置文件。"""
        if not os.path.exists(self.config_file_path):
            raise FileNotFoundError(f"Config file not found: {self.config_file_path}")
        with open(self.config_file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)


class LLMChatClient(BaseVolcengineClient):
    """
    大语言模型对话客户端。
    用于发起文本对话请求，默认加载 API_CZ.yaml 和模型配置 model_set.yaml。
    """
    
    def __init__(self, config_file_name="API_CZ.yaml", default_model="Doubao-2.0"):
        """
        初始化对话客户端。
        
        Args:
            config_file_name (str): 配置文件名，默认 "API_CZ.yaml"。文件需存放在 utils/docs/ 目录下。
            default_model (str): 默认使用的模型名称，必须与 YAML 里的 key 以及 model_set.yaml 里的 choose_by 对应。
        """
        config_path = os.path.join(DOCS_DIR, config_file_name)
        super().__init__(config_path)
        self.default_model = default_model
        
        # 从 model_set.yaml 加载各个模型的调用参数 (如 temperature, max_tokens 等)
        self.model_set_path = os.path.join(DOCS_DIR, "model_set.yaml")
        self.model_params = self._load_model_params()
        
    def _load_model_params(self) -> dict:
        """解析 model_set.yaml，将参数按照模型名称映射为字典。"""
        params = {}
        if not os.path.exists(self.model_set_path):
            return params
            
        with open(self.model_set_path, "r", encoding="utf-8") as f:
            docs = yaml.safe_load_all(f)
            for doc in docs:
                if doc and "choose_by" in doc:
                    model_name = doc.pop("choose_by")
                    params[model_name] = doc
        return params

    def get_response(self, user_input: str, system_prompt: str = "", model: str = None) -> str:
        """
        发起一次同步的对话补全请求，并返回文本结果。
        
        Args:
            user_input (str): 用户的提问内容。
            system_prompt (str): 可选的系统提示词（人设、规则等）。
            model (str): 指定要调用的模型名称。若不传则使用初始化时的 default_model。
            
        Returns:
            str: 模型返回的文本结果。如果出错则返回错误信息。
        """
        model = model or self.default_model
        
        # 从配置文件中获取实际的模型接入点 (endpoint)
        ep = self.config.get("model_ep", {}).get(model)
        if not ep:
            raise ValueError(f"Endpoint for model '{model}' not found in {self.config_file_path}")
            
        # 组装消息列表
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_input})
        
        # 获取该模型在 model_set.yaml 中配置的调用参数
        kwargs = self.model_params.get(model, {}).copy()
        
        # 强制覆盖部分参数以保证同步文本调用的正确性
        kwargs["stream"] = False
        kwargs["model"] = ep
        kwargs["messages"] = messages
        
        try:
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            return f"Error calling chat model: {e}"


class EmbeddingClient(BaseVolcengineClient):
    """
    文本向量化 (Embedding) 客户端。
    用于将文本转化为向量，默认加载 API_DR.yaml 配置文件。
    """
    
    def __init__(self, config_file_name="API_DR.yaml", default_model="Doubao-Embedding"):
        """
        初始化向量化客户端。
        
        Args:
            config_file_name (str): 配置文件名，默认 "API_DR.yaml"。文件需存放在 utils/docs/ 目录下。
            default_model (str): 默认使用的 Embedding 模型名称。
        """
        config_path = os.path.join(DOCS_DIR, config_file_name)
        super().__init__(config_path)
        self.default_model = default_model
        
        # Embedding 服务在 API_DR.yaml 中使用了专用的 EMB_API_KEY
        # 如果未配置，则降级使用默认的 ARK_API_KEY
        self.api_key = self.config.get("EMB_API_KEY", self.config.get("ARK_API_KEY"))
        # 使用正确的 API Key 重新初始化 client
        self.client = Ark(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
    def get_embedding(self, text: str, model: str = None) -> list:
        """
        获取单段文本的 Embedding 向量。
        
        Args:
            text (str): 需要向量化的单段文本。
            model (str): 指定的模型名称，不传则使用默认模型。
            
        Returns:
            list: 浮点数组成的向量列表（如 [0.12, -0.45, ...]）。如果失败则返回空列表 []。
        """
        model = model or self.default_model
        ep = self.config.get("emb_model", {}).get(model)
        
        if not ep:
            raise ValueError(f"Endpoint for embedding model '{model}' not found in {self.config_file_path}")
            
        try:
            response = self.client.embeddings.create(
                model=ep,
                input=[text]
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error calling embedding model: {e}")
            return []
            
    def get_embeddings(self, texts: list, model: str = None) -> list:
        """
        批量获取多段文本的 Embedding 向量。
        
        Args:
            texts (list): 需要向量化的文本列表，如 ["文本1", "文本2"]。
            model (str): 指定的模型名称，不传则使用默认模型。
            
        Returns:
            list: 嵌套的向量列表，形如 [[向量1...], [向量2...]]。如果失败则返回空列表 []。
        """
        model = model or self.default_model
        ep = self.config.get("emb_model", {}).get(model)
        
        if not ep:
            raise ValueError(f"Endpoint for embedding model '{model}' not found in {self.config_file_path}")
            
        try:
            response = self.client.embeddings.create(
                model=ep,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            print(f"Error calling embedding model: {e}")
            return []

