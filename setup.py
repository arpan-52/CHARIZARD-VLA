from setuptools import setup, find_packages

# Read README.md
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="charizard-vla",
    version="0.1.0",
    author="Arpan Pal",
    author_email="arpan522000@gmail.com",
    description="VLA data processing package with polarization and self-calibration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/arpanastrobot/charizard-vla",  # Replace with your GitHub URL
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Astronomy",
    ],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "charizard-vla=charizard_vla.pokeegg:main",
        ],
    },
    install_requires=[
        # Add your package dependencies here
        # Example:
        # "numpy>=1.18.0",
        # "astropy>=4.0",
    ],
)