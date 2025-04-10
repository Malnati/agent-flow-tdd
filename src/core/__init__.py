"""
kernel package - Utilitários e ferramentas do framework
"""

import logging
from src.core.models import ModelManager
from src.core.version import VersionAnalyzer

logger = logging.getLogger(__name__)

__all__ = ['ModelManager', 'VersionAnalyzer']

