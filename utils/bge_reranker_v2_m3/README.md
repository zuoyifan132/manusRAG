# BGE Reranker v2 m3 Installation and Usage Guide

## Overview

The BAAI/bge-reranker-v2-m3 is a powerful multilingual reranker model developed by the Beijing Academy of Artificial Intelligence. This lightweight reranker model (568MB) possesses strong multilingual capabilities, is easy to deploy, and provides fast inference.

Rerankers are crucial components in modern retrieval systems. Unlike embedding models that output vector representations, rerankers take a query and document as input to directly output a relevance score. This model is particularly useful for improving the accuracy of retrieval systems by reranking candidate documents retrieved by first-stage retrievers.

## Installation

### Navigate to the BGE Reranker Directory

First, navigate to the BGE Reranker directory:

```bash
cd utils/bge_reranker_v2_m3
```

All the following commands should be executed from this directory.

### Download and Set Up the Model

To download and set up the BGE Reranker model, you can simply run:

```bash
python app.py
```

or

```bash
bash run_reranker.sh
```

This will automatically download the model (approximately 568MB in size) and start the reranker service. The first run may take longer as it downloads the model.

Then check the log file to monitor the process if you used bash script(bash run_reranker.sh):

```bash
tail -f minerU_app.log
```

When you see the following output, it indicates that the model was successfully downloaded, loaded, and the service is running properly:

```
2025-04-22 16:30:59.467 | INFO     | __main__:<module>:19 - Loading BGE-Reranker-v2-m3 model...
2025-04-22 16:31:04.721 | INFO     | __main__:<module>:24 - Model loaded successfully.
2025-04-22 16:31:04.724 | INFO     | __main__:<module>:84 - Starting FastAPI service on 0.0.0.0:12212...
INFO:     Started server process [21852]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:12212 (Press CTRL+C to quit)
```

## Features

The BAAI/bge-reranker-v2-m3 model offers the following features:

- **Multilingual Support**: Provides strong multilingual reranking capabilities
- **Lightweight**: Only 568MB in size, making it easy to deploy in various environments
- **Fast Inference**: Optimized for speed without compromising performance
- **High Accuracy**: Delivers state-of-the-art performance on various reranking benchmarks
- **Easy Integration**: Designed to work seamlessly with retrieval systems

## Usage

The reranker service exposes an API endpoint that can be used to compute relevance scores between query-document pairs. You can use this API in your retrieval pipeline to improve search results.

### API Endpoint

The reranker service exposes the following endpoint:

- `POST /rerank`: Reranks a list of documents based on their relevance to a query

### Stopping the Service

To stop the reranker service, you can press `CTRL+C` in the terminal where the service is running.

## Technical Details

- **Base Model**: The model is built on top of the bge-m3 model from BAAI
- **Parameters**: 568M parameters
- **Tensor Type**: FP32
- **License**: Apache-2.0

## Performance

The BGE Reranker v2 m3 model has been evaluated on various benchmarks including BEIR, CMTEB-retrieval, and MIRACL multilingual benchmarks, showing strong performance across different languages and domains.

## Acknowledgements

This model was developed by the Beijing Academy of Artificial Intelligence (BAAI). For more information, please refer to the [official repository](https://github.com/FlagOpen/FlagEmbedding).

## Citation

If you use this model in your research, please cite the following papers:

```bibtex
@misc{li2023making,
      title={Making Large Language Models A Better Foundation For Dense Retrieval}, 
      author={Chaofan Li and Zheng Liu and Shitao Xiao and Yingxia Shao},
      year={2023},
      eprint={2312.15503},
      archivePrefix={arXiv},
      primaryClass={cs.CL}
}
@misc{chen2024bge,
      title={BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation}, 
      author={Jianlv Chen and Shitao Xiao and Peitian Zhang and Kun Luo and Defu Lian and Zheng Liu},
      year={2024},
      eprint={2402.03216},
      archivePrefix={arXiv},
      primaryClass={cs.CL}
}
``` 