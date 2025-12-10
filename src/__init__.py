"""
Singapore Economic Stress Monitor - Source Package

This package contains all the core modules for the stress scoring system:
- data_loader: Load and align economic indicator data
- normalizer: Z-score normalization and transformation
- stress_scorer: Composite score calculation and alert classification
- visualizer: Chart generation for dashboard output
"""

__version__ = '1.0.0'
__author__ = 'Singapore Economic Stress Monitor'

# Package-level imports for convenience
from . import data_loader
from . import normalizer
from . import stress_scorer
from . import visualizer

__all__ = [
    'data_loader',
    'normalizer',
    'stress_scorer',
    'visualizer'
]
