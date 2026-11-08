"""DraftMaster AI autonomous growth engine."""
from setuptools import find_packages, setup

setup(
    name="draftmaster-growth",
    version="1.0.0",
    description="DraftMaster AI autonomous growth engine (content, outreach, self-improvement)",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=["httpx>=0.27", "draftmaster-engine"],
)
