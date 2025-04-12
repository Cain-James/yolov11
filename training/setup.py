from setuptools import setup, find_packages

setup(
    name="yolov11-training",
    version="0.1",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "torch>=2.0.0",
        "torchvision>=0.15.0",
        "numpy>=1.21.0",
        "opencv-python>=4.5.0",
        "albumentations>=1.3.0",
        "PyYAML>=5.4.0",
    ],
    python_requires=">=3.8",
) 