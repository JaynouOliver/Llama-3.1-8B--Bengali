import json
import argparse
from tqdm import tqdm

from datasets import load_dataset
from tokenizers import SentencePieceBPETokenizer
from transformers import LlamaTokenizerFast, AutoTokenizer

def main(args):
    # Load the dataset from the huggingface Hub and prepare it for training
    if args.dataset_name is not None:
        dataset = load_dataset(args.dataset_name, 
            split=args.dataset_split, 
            token=args.hub_token if args.hub_token else None,
        )
    else:
        raise ValueError("No dataset name provided") 

    # Remove non text columns
    dataset = dataset.remove_columns([col for col in dataset.column_names if col != "text"])

    # select `num_samples` from the dataset
    dataset = dataset.shuffle(seed=42).select(range(args.num_samples))

    # Create a SentencePieceBPETokenizer
    tokenizer = SentencePieceBPETokenizer()

    # Train the SentencePieceBPETokenizer on the dataset
    tokenizer.train_from_iterator(
        iterator=dataset['text'],
        vocab_size=args.vocab_size,
        show_progress=True,
        special_tokens=["<unk>", "<s>", "</s>", "<pad>"],
    )

    # Save the tokenizer
    tokenizer.save("hindi-sentencepiece-tokenizer.json", pretty=True)

    # Load reference tokenizer
    if args.reference_tokenizer is not None and args.hub_token is not None:
        reference_tokenizer = AutoTokenizer.from_pretrained(args.reference_tokenizer, token=args.hub_token if args.hub_token else None)
        reference_tokenizer.save_pretrained("reference-tokenizer")
    else:
        raise ValueError("No tokenizer name provided or no hub token provided. Try using `--reference_tokenizer 'meta-llama/Llama-2-7b-hf'")

    # Read and dump the json file for the new tokenizer and the reference tokenizer
    with open("hindi-sentencepiece-tokenizer.json") as f:
        new_llama_tokenizer_json = json.load(f)

    with open("reference-tokenizer/tokenizer.json") as f:
        reference_tokenizer_json = json.load(f)
    
    # Add the reference tokenizer's config to the new tokenizer's config
    new_llama_tokenizer_json["normalizer"] = reference_tokenizer_json["normalizer"]
    new_llama_tokenizer_json["pre_tokenizer"] = reference_tokenizer_json["pre_tokenizer"]
    new_llama_tokenizer_json["post_processor"] = reference_tokenizer_json["post_processor"]
    new_llama_tokenizer_json["decoder"] = reference_tokenizer_json["decoder"]
    new_llama_tokenizer_json["model"]['fuse_unk'] = reference_tokenizer_json["model"]['fuse_unk']
    new_llama_tokenizer_json["model"]['byte_fallback'] = reference_tokenizer_json["model"]['byte_fallback']

    # Dump the new tokenizer's config
    with open("hindi-sentencepiece-tokenizer.json", "w") as f:
        json.dump(new_llama_tokenizer_json, f, indent=2, ensure_ascii=False)

    # Load the new tokenizer as a LlamaTokenizerFast
    new_llama_tokenizer = LlamaTokenizerFast(
        tokenizer_file="hindi-sentencepiece-tokenizer.json",
        unk_token="<unk>",
        unk_token_id=0,
        bos_token="<s>",
        bos_token_id=1,
        eos_token="</s>",
        eos_token_id=2,
        pad_token="<pad>",
        pad_token_id=3,
        padding_side="right",
    )

    # Save the new tokenizer
    new_llama_tokenizer.save_pretrained("hindi-llama-tokenizer")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train a new Hindi Llama tokenizer")
    parser.add_argument(
        "--dataset_name",
        type=str,
        default="zicsx/mC4-Hindi-Cleaned-3.0",
        help="The name of the dataset to be tokenized",
    )
    parser.add_argument(
        "--dataset_split",
        type=str,
        default="train",
        help="The split of the dataset to be tokenized",
    )
    parser.add_argument(
        "--hub_token",
        type=str,
        required=True,
        help="The token to access the dataset on the hub",
    )
    parser.add_argument(
        "--reference_tokenizer",
        type=str,
        default="meta-llama/Llama-2-7b-hf",
        help="The name of the reference tokenizer to use",
    )
    parser.add_argument(
        "--num_samples",
        type=int,
        default=200000,
        help="Number of samples to use from the dataset",
    )
    parser.add_argument(
        "--vocab_size",
        type=int,
        default=32000,
        help="Vocabulary size to use for the tokenizer",
    )
    args = parser.parse_args()
    main(args)