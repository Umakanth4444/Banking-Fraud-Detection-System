import argparse
from src.db import test_connection
from src.data import load_data, get_overview
from src.model import train_model

def main():
    parser = argparse.ArgumentParser(description="Banking Fraud Detection SQL Project")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("test-db")
    load = commands.add_parser("load-data")
    load.add_argument("--replace", action="store_true")
    commands.add_parser("summary")
    commands.add_parser("train")
    args = parser.parse_args()
    if args.command == "test-db":
        print(test_connection())
    elif args.command == "load-data":
        print(f"Loaded {load_data(replace=args.replace)} transactions.")
    elif args.command == "summary":
        print(get_overview())
    elif args.command == "train":
        result = train_model()
        print(result["report"])
        print("Confusion matrix:", result["confusion_matrix"])
        print("ROC-AUC:", result["roc_auc"])
        print("Model saved:", result["model_path"])

if __name__ == "__main__":
    main()
