"""DraftMaster AI strategy engine."""
from setuptools import find_packages, setup

setup(
    name="draftmaster-engine",
    version="1.0.0",
    description="DraftMaster AI strategy engine (pure-Python strategy core)",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=["httpx>=0.27", "numpy>=1.26", "Pillow>=10.3"],
)
