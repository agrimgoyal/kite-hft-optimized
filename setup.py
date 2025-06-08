"""
Setup script for Kite HFT Optimized Trading System
"""

from setuptools import setup, find_packages, Extension
from Cython.Build import cythonize
import numpy

# Optional Cython extensions for performance
cython_extensions = [
    Extension(
        "src.utils.fast_math",
        ["src/utils/fast_math.pyx"],
        include_dirs=[numpy.get_include()],
        extra_compile_args=["-O3", "-ffast-math"],
        language_level=3,
    ),
    Extension(
        "src.datafeed.tick_processor",
        ["src/datafeed/tick_processor.pyx"],
        include_dirs=[numpy.get_include()],
        extra_compile_args=["-O3", "-ffast-math"],
        language_level=3,
    ),
]

# Read README for long description
try:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = "High-performance trading system for Kite Connect API"

# Read requirements
with open("requirements.txt", "r") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="kite-hft-optimized",
    version="2.0.0",
    author="Trading Team",
    author_email="trading@example.com",
    description="High-performance trading system for Kite Connect API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/kite-hft-optimized",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
        ],
        "performance": [
            "Cython>=0.29.0",
            "numba>=0.57.0",
        ],
        "gui": [
            "streamlit>=1.28.0",
            "plotly>=5.17.0",
        ],
        "notifications": [
            "python-telegram-bot>=20.0",
            "sendgrid>=6.10.0",
        ],
        "database": [
            "sqlalchemy>=2.0.0",
            "redis>=4.5.0",
        ],
    },
    ext_modules=cythonize(cython_extensions, compiler_directives={"language_level": 3}),
    include_dirs=[numpy.get_include()],
    entry_points={
        "console_scripts": [
            "kite-hft=src.main:main",
            "kite-monitor=src.monitoring.dashboard:main",
        ],
    },
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.md", "*.txt"],
    },
    include_package_data=True,
    zip_safe=False,
)