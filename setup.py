from setuptools import setup, find_packages
setup(
    name="charizard-vla",
    version="0.1.0",
    author="Arpan Pal",
    author_email="arpan522000@gmail.com",
    description="VLA data processing package",
    packages=find_packages(),
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "charizard-vla=charizard_vla.pokeegg:main",
        ],
    },
)