# MinerU Installation and Usage Guide

MinerU is a powerful PDF parsing tool that converts PDF documents into markdown files. It provides high-quality document content extraction capabilities for various document types.

## Table of Contents

- [Installation](#installation)
- [Setting up the Virtual Environment](#setting-up-the-virtual-environment)
- [Installing Required Packages](#installing-required-packages)
- [Downloading Models](#downloading-models)
- [Running MinerU](#running-minerU)
- [Stopping MinerU](#stopping-minerU)
- [Features](#features)
- [Troubleshooting](#troubleshooting)

## Installation

### Navigate to the MinerU App Directory

First, navigate to the minerU_app directory:

```bash
cd utils/minerU_app
```

All the following commands should be executed from this directory.

### Setting up the Virtual Environment

Create a virtual environment for MinerU:

```bash
conda create -n manusRAG python=3.10
conda activate manusRAG
```

### Installing Required Packages

After activating the environment, install the required packages:

```bash
pip install -r requirements.txt
```

This will install the following main dependencies:
- magic-pdf[full]
- fastapi
- uvicorn
- python-multipart

### Downloading Models

Run the model downloader script to download the built-in MinerU models (approximately 2GB of storage space is required):

```bash
python download_models.py
```

This script will download the necessary models for layout analysis, OCR, formula detection, and other components required by MinerU.

## Running MinerU

To start the MinerU service:

```bash
bash run_minerU_app.sh
```

Then check the log file to monitor the process:

```bash
tail -f minerU_app.log
```

When you see the following output, it indicates that the installation and execution are working correctly:

```
INFO:     Started server process [xxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8888 (Press CTRL+C to quit)
```

## Stopping MinerU

To stop the MinerU service:

```bash
bash kill_minerU.sh
```

This script will terminate any processes running on port 8888.

## Features

MinerU is a powerful PDF parsing tool with the following capabilities:

- Extraction of structured content from PDFs
- Conversion of PDF documents to markdown format
- Preservation of document layout and formatting
- Recognition of text, tables, images, and formulas
- Multilingual support for document analysis
- High-quality OCR for scanned documents

MinerU uses advanced AI models to analyze document structure and extract content with high accuracy, making it an excellent tool for document analysis and data extraction workflows.

## Troubleshooting

If you encounter any issues:

1. Ensure that your Python environment is correctly set up with Python 3.10
2. Check that all required dependencies are installed
3. Verify that the model downloading process completed successfully
4. Examine the log file at `minerU_app.log` for any error messages
5. Ensure port 8888 is not being used by another application

For more information about MinerU, visit the [MinerU GitHub repository](https://github.com/opendatalab/MinerU).
