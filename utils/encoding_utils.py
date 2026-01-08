"""
文件编码工具模块
提供健壮的文件编码检测和读取功能
"""

from pathlib import Path
from typing import Optional
from loguru import logger

# 可选的 chardet 库导入尝试
try:
    import chardet
    CHARDET_AVAILABLE = True
except ImportError:
    CHARDET_AVAILABLE = False
    logger.info("chardet library not available, will use fallback encoding detection")


def detect_encoding(file_path: Path) -> str:
    """
    检测文件编码
    
    Args:
        file_path: 文件路径
        
    Returns:
        检测到的编码名称
    """
    try:
        # 首先尝试使用 chardet
        if CHARDET_AVAILABLE:
            with open(file_path, 'rb') as f:
                raw_data = f.read(100000)  # 读取前100KB
                result = chardet.detect(raw_data)
                encoding = result.get('encoding', 'utf-8')
                confidence = result.get('confidence', 0)
                
                if encoding and confidence > 0.5:
                    logger.info(f"Detected encoding '{encoding}' (confidence: {confidence:.2f}) for {file_path}")
                    
                    # chardet 可能返回 'GB2312' 或 'GB18030'，统一使用 'GBK'
                    if encoding.lower() in ['gb2312', 'gb18030']:
                        return 'gbk'
                    return encoding
        
        # 如果没有 chardet 或者置信度低，尝试手动检测
        return _manual_detect_encoding(file_path)
        
    except Exception as e:
        logger.warning(f"Encoding detection failed for {file_path}: {e}, defaulting to utf-8")
        return 'utf-8'


def _manual_detect_encoding(file_path: Path) -> str:
    """
    手动检测文件编码
    
    Args:
        file_path: 文件路径
        
    Returns:
        检测到的编码名称
    """
    try:
        # 尝试 UTF-8（带BOM和无BOM）
        with open(file_path, 'rb') as f:
            raw_data = f.read(4)
            if raw_data.startswith(b'\xef\xbb\xbf'):
                return 'utf-8-sig'
        
        # 尝试 UTF-8（宽松模式）
        file_path.read_text(encoding='utf-8', errors='strict')
        return 'utf-8'
    except UnicodeDecodeError as e:
        logger.debug(f"UTF-8 decode failed for {file_path}: {e}")
    
    # 尝试 GBK
    try:
        file_path.read_text(encoding='gbk', errors='strict')
        return 'gbk'
    except UnicodeDecodeError:
        pass
    
    # 尝试 GB18030
    try:
        file_path.read_text(encoding='gb18030', errors='strict')
        return 'gb18030'
    except UnicodeDecodeError:
        pass
    
    # 默认返回 utf-8，使用容错模式读取
    logger.warning(f"Could not detect encoding for {file_path}, defaulting to utf-8 with fallback")
    return 'utf-8'


def read_file_robust(file_path: Path, encoding: Optional[str] = None) -> str:
    """
    健壮地读取文件内容，自动处理编码问题
    
    Args:
        file_path: 文件路径
        encoding: 指定编码（如果为None则自动检测）
        
    Returns:
        文件内容字符串
        
    Raises:
        FileNotFoundError: 文件不存在
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # 如果未指定编码，自动检测
    if encoding is None:
        encoding = detect_encoding(file_path)
    
    # 首先尝试正常读取
    try:
        logger.debug(f"Trying to read {file_path} with encoding: {encoding}")
        return file_path.read_text(encoding=encoding)
    except UnicodeDecodeError as e:
        logger.warning(f"UnicodeDecodeError reading {file_path} with {encoding}: {e}")
        
        # 如果当前编码是utf-8，先尝试使用错误处理
        if encoding.lower().startswith('utf-8'):
            logger.debug(f"Trying UTF-8 with errors='replace'")
            return file_path.read_text(encoding='utf-8', errors='replace')
        
        # 尝试使用其他编码
        for fallback_encoding in ['utf-8', 'gbk', 'gb18030', 'utf-8-sig']:
            if fallback_encoding != encoding:
                try:
                    logger.debug(f"Trying fallback encoding: {fallback_encoding}")
                    return file_path.read_text(encoding=fallback_encoding)
                except UnicodeDecodeError:
                    logger.debug(f"Failed with {fallback_encoding}")
                    continue
        
        # 最后手段：使用最强容错模式
        logger.warning(f"All encoding attempts failed for {file_path}, using 'ignore' mode")
        return file_path.read_text(encoding='utf-8', errors='ignore')


def write_file_robust(file_path: Path, content: str, encoding: str = 'utf-8') -> bool:
    """
    写入文件内容
    
    Args:
        file_path: 文件路径
        content: 要写入的内容
        encoding: 编码格式
        
    Returns:
        是否成功
    """
    try:
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        file_path.write_text(content, encoding=encoding)
        logger.info(f"Successfully wrote file: {file_path} (encoding: {encoding})")
        return True
        
    except UnicodeEncodeError as e:
        logger.error(f"UnicodeEncodeError writing {file_path} with {encoding}: {e}")
        # 尝试使用UTF-8带SIG（适用于Windows）
        if encoding.lower() != 'utf-8-sig':
            try:
                logger.info(f"Retrying with utf-8-sig encoding for {file_path}")
                file_path.write_text(content, encoding='utf-8-sig')
                logger.info(f"Successfully wrote file with utf-8-sig: {file_path}")
                return True
            except Exception as e2:
                logger.error(f"Failed to write {file_path} even with utf-8-sig: {e2}")
        return False
        
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        return False
