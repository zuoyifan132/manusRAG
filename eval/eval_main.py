# -*- coding: utf-8 -*-
# Created on 2024/8/26
import logging
from tqdm import tqdm
from pypinyin import pinyin, lazy_pinyin, Style

from utilities import (
    read_excel,
    flash_rag_ingest,
    flash_rag_search,
    save_data_to_jsonl,
    print_and_save_metrics,
    group_questions_by_doc,
)
from eval.answer_correctness_custom import (
    answer_correctness_multi_GT_eval,
    answer_correctness_single_GT_eval
)
from metric import single_hit, single_question_recall_rate


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

RETRIEVAL_TOP_K = 10


def eval_single_doc(
        question_ground_truth_path: str,
        prompt_template: str = "ZH_SINGLE_CORRECTNESS_INSTRUCTIONS",
        save_metric_path: str=r"D:\yfzuo\YUN\rest\RAG\RAG_metadata\rag_metadata_eval\answer_correctness_custom\eval_metric.txt",
        output_path=None,
        eval_desc="",
):
    # read and group questions with doc
    eval_data = read_excel(question_ground_truth_path)
    grouped_data = group_questions_by_doc(eval_data)

    count, total_hit, total_recall = 0, 0, 0.0
    save_data = []

    for doc_name, gt_chunks_and_path in tqdm(grouped_data.items(), desc="Evaluating docs: "):
        doc_path = gt_chunks_and_path.get("pdf_path", None)
        print("doc_path: ", doc_path)

        # test single doc collection existence then ingest data into the database
        collection_name=f"{"".join(lazy_pinyin(doc_name))}_rag_eval_collection"
        dummy_search_res = flash_rag_search(
            query="dummy query", 
            top_k=RETRIEVAL_TOP_K, 
            collection_name=collection_name
        )
        print("dummy_search_res: ",dummy_search_res)
        if dummy_search_res["status"] == "failed" and dummy_search_res["search_results_count"] == 0:
            logging.info(f"{collection_name} doesn't exists in the database, starting ingest...")
            flash_rag_ingest_res = flash_rag_ingest(pdf_path=doc_path, collection_name=collection_name)
            print("flash_rag_ingest_res: ", flash_rag_ingest_res)
        else:
            logging.info(f"{collection_name} exists in the database, skipping ingest...")

        # get questions with specific doc
        question_labels = grouped_data.get(doc_name, None).get("chunks", None)
        if question_labels is None:
            logging.warning(f"{doc_name} question do not exists")
            continue

        # evaluation method
        if prompt_template == "ZH_MULTI_CORRECTNESS_INSTRUCTIONS":
            evaluation_method = answer_correctness_multi_GT_eval
        elif prompt_template == "ZH_SINGLE_CORRECTNESS_INSTRUCTIONS":
            evaluation_method = answer_correctness_single_GT_eval
        else:
            logging.warning(f"{prompt_template} invalid")
            return

        # evaluation process
        for each_question_labels in tqdm(question_labels, desc="each doc questions: "):
            question = each_question_labels[0]
            ground_truth = each_question_labels[4:]
            ground_truth = [s for s in ground_truth if len(s) > 3]

            print("question: ", question)
            print("ground_truth: ", ground_truth)

            # retrieval from rag
            try:
                retrieval_res = flash_rag_search(
                    query=question, 
                    top_k=RETRIEVAL_TOP_K, 
                    collection_name=collection_name
                )

                if retrieval_res["status"] == "failed":
                    raise ValueError(f"retrieval in collection: {collection_name} with query: {question} failed due to {retrieval_res["reason"]}")
                else:
                    retrieval_chunks = [obj["chunk"] for obj in retrieval_res["search_results"]]
            except Exception as e:
                logging.error(f"Unexpected error during retrieval for query '{question}': {e}")
                raise
            
            # evaluation process 
            success, tp, fp = evaluation_method(
                answer=retrieval_chunks,
                ground_truth=ground_truth,
                prompt_template=prompt_template
            )
            if success:
                print("all tp: ", tp)
                print("all fp: ", fp)
                save_data.append({
                    "query": question,
                    "valid_ground_truth: ": ground_truth,
                    "chunks": retrieval_chunks,
                    "TP": tp,
                    "fp": fp
                })
            else:
                logging.warning(f"answer_correctness_eval failed for {question}")

            # calculate evaluation stats
            total_hit += 1 if single_hit(tp) else 0
            total_recall += single_question_recall_rate(tp, ground_truth)
            count += 1

    if output_path is not None:
        save_data_to_jsonl(save_data, output_path)

    # print and save the metric to eval_metric.txt
    print_and_save_metrics(
        total_hit=total_hit,
        count=count,
        total_recall=total_recall,
        experiment_details=eval_desc,
        save_metric_path=save_metric_path,
        output_path=output_path,
        question_ground_truth_path=question_ground_truth_path,
        prompt_template=prompt_template
    )


def main():
    eval_single_doc(
        question_ground_truth_path=r"/mnt/storage/yfzuo/flashC_project/rag/eval/eval_data/labels_cross_chunk.xlsx",
        prompt_template="ZH_MULTI_CORRECTNESS_INSTRUCTIONS",
        output_path=r"/mnt/storage/yfzuo/flashC_project/rag/eval/eval_output/single_doc_eval_res.jsonl",
        save_metric_path=r"/mnt/storage/yfzuo/flashC_project/rag/eval/eval_metric.txt",
        eval_desc="single doc multi ground truth prompt test",
    )


if __name__ == "__main__":
    main()