import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('requirements.txt', 'r') as f:
    install_requires = f.read().split('\n')[:-1]

setuptools.setup(
     name='urbanpy',
     version='0.2',
     author="Andres Regal, Claudio Ortega",
     author_email="a.regalludowieg@up.edu.pe",
     description="A library to download, process and visualize high resolution urban data.",
     long_description=long_description,
     long_description_content_type="text/markdown",
     url="https://github.com/IngenieriaUP/urbanpy",
     packages=setuptools.find_packages(),
     classifiers=[
         "Programming Language :: Python :: 3",
         "Operating System :: OS Independent",
     ],
     install_requires=install_requires,
     python_requires='>=3.6'
 )
