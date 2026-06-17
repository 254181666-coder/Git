import os
from dotenv import load_dotenv
from functools import lru_cache

load_dotenv()


class Settings:
    # 数据库配置 - 支持SQLite和MySQL
    DB_TYPE: str = os.environ.get("DB_TYPE", "sqlite")
    DB_HOST: str = os.environ.get("DB_HOST", "localhost")
    DB_PORT: int = int(os.environ.get("DB_PORT", "3306"))
    DB_USER: str = os.environ.get("DB_USER", "root")
    DB_PASSWORD: str = os.environ.get("DB_PASSWORD", "")
    DB_NAME: str = os.environ.get("DB_NAME", "attendance")
    
    @property
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE.lower() == "sqlite":
            return "sqlite:///./attendance.db"
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    # 应用配置
    APP_NAME: str = os.environ.get("APP_NAME", "考勤工资管理系统")
    APP_VERSION: str = os.environ.get("APP_VERSION", "1.0.0")
    APP_HOST: str = os.environ.get("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.environ.get("APP_PORT", "8000"))

    # CORS 配置
    CORS_ORIGINS: list = os.environ.get("CORS_ORIGINS", "null,http://localhost:8010,http://127.0.0.1:8010").split(",")

    # 管理员账号配置
    ADMIN_USERNAME: str = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "test123")

    # 密钥配置
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # 其他配置
    RATE_LIMIT: int = 100
    RATE_WINDOW: int = 60


@lru_cache()
def get_settings():
    return Settings()
