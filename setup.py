from setuptools import setup, find_packages

setup(
    name="yolov11",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask',
        'flask-cors',
        'opencv-python',
        'numpy',
        'torch',
        'ultralytics',
        'pillow'
    ],
    python_requires='>=3.8',
) 