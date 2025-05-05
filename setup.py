from setuptools import find_packages, setup

with open("app/README.md", "r") as f:
    long_description = f.read()

setup(
    name="github_data_extractor",
    version="0.0.10",
    description="A package to extract GitHub repository insights",
    package_dir={"": "app"},
    packages=find_packages(where="app"),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aadityayadav/github_data_extractor",
    author="Aaditya Yadav/ Vibhak Golchha",
    author_email="aadityayadav2003@gmail.com, vibhakgolchha@gmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.5",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "pydriller>=1.9",
        "PyGithub>=1.54",
        "requests>=2.20.0"],
    extras_require={
        "dev": ["pytest>=7.0", "twine>=4.0.2", "python-dotenv>=1.0.0", "wheel>=0.37.0"],
    },
    python_requires=">=3.5",
)