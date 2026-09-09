"""
JWT 认证工具
包含 access/refresh token 的签发与验证、密码哈希校验、数据加密解密。
"""

from base64 import b64decode, b64encode
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from cryptography.fernet import Fernet
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与哈希值是否匹配"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    创建 JWT access token
    Args:
        data: 载荷数据（必须包含 "sub" 字段）
        expires_delta: 过期时间，默认使用配置值
    Returns:
        编码后的 JWT 字符串
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    创建 JWT refresh token（较长过期时间）
    Args:
        data: 载荷数据
    Returns:
        编码后的 JWT 字符串
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    解码并验证 JWT token
    Args:
        token: JWT 字符串
    Returns:
        解码后的载荷字典
    Raises:
        JWTError: 令牌无效或已过期
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        raise JWTError(f"Token 无效或已过期: {e}") from e


# ---------- 数据加密 / 解密 ----------


def _get_fernet() -> Fernet:
    """
    从 SECRET_KEY 派生 Fernet 密钥

    SECRET_KEY 可能不是合法的 32 字节 base64 编码，
    使用 SHA-256 哈希均匀映射后再 base64 编码。
    """
    import hashlib

    raw_key = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    fernet_key = b64encode(raw_key)
    return Fernet(fernet_key)


def encrypt_password(plain_password: str) -> str:
    """
    加密数据库密码

    Args:
        plain_password: 明文密码

    Returns:
        Fernet 加密后的 base64 字符串
    """
    fernet = _get_fernet()
    token = fernet.encrypt(plain_password.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_password(encrypted_password: str) -> str:
    """
    解密数据库密码

    Args:
        encrypted_password: Fernet 加密的密码字符串

    Returns:
        明文密码
    """
    fernet = _get_fernet()
    token = fernet.decrypt(encrypted_password.encode("utf-8"))
    return token.decode("utf-8")