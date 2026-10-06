"""全局配置：API KEY、模型、路径、Mock 模式。

通过环境变量 / .env 文件配置。所有配置集中在 settings 单例中。
"""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent


def _load_env_file(path: Path) -> None:
    """轻量 .env 解析（不依赖 python-dotenv）。"""
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:  # 已存在的环境变量优先
                os.environ[key] = value
    except Exception:
        pass


# 依次加载项目根目录与 backend 目录下的 .env
_load_env_file(PROJECT_DIR / ".env")
_load_env_file(BACKEND_DIR / ".env")

# 不同大模型服务商的默认 Base URL（均为 OpenAI 兼容协议）
DEFAULT_BASE_URLS = {
    "deepseek": "https://api.deepseek.com/v1",
    "doubao": "https://ark.cn-beijing.volces.com/api/v3",
    "openai": "https://api.openai.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}

DEFAULT_MODELS = {
    "deepseek": "deepseek-chat",
    "doubao": "",  # 豆包需在 .env 中填写 Endpoint ID
    "openai": "gpt-4o-mini",
    "qwen": "qwen-plus",
}


class Settings:
    """系统运行配置。"""

    def __init__(self) -> None:
        # ---- 大模型 ----
        self.llm_provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()
        self.llm_api_key = os.getenv("LLM_API_KEY", "").strip()
        self.llm_base_url = os.getenv("LLM_BASE_URL", "").strip()
        self.llm_model = (
            os.getenv("LLM_MODEL", "").strip()
            or DEFAULT_MODELS.get(self.llm_provider, "deepseek-chat")
        )
        self.llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.llm_timeout = float(os.getenv("LLM_TIMEOUT", "120"))
        self.llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4000"))

        # ---- 向量 / Embedding ----
        self.embedding_provider = os.getenv("EMBEDDING_PROVIDER", "hash").strip().lower()
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

        # ---- 路径 ----
        self.data_dir = Path(os.getenv("DATA_DIR", str(PROJECT_DIR / "data")))
        self.chroma_dir = self.data_dir / "chroma"
        self.uploads_dir = self.data_dir / "uploads"
        self.db_path = self.data_dir / "app.db"
        self.vector_path = self.data_dir / "vector_store.json"
        self.static_dir = self.data_dir / "static"

        # ---- 服务 ----
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.cors_origins = [
            o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
        ]

    # ---------- 派生属性 ----------
    @property
    def llm_available(self) -> bool:
        """是否配置了真实大模型 API。"""
        return bool(self.llm_api_key) and self.llm_provider != "mock"

    @property
    def mock_mode(self) -> bool:
        """是否处于离线演示（Mock）模式。"""
        return not self.llm_available

    @property
    def base_url(self) -> str:
        return self.llm_base_url or DEFAULT_BASE_URLS.get(self.llm_provider, "")

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.chroma_dir, self.uploads_dir, self.static_dir):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
