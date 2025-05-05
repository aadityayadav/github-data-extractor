from github_data_extractor import dataExtraction
from dotenv import load_dotenv
import os


load_dotenv()
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

def main():
    repo_name = ['translate_lib']
    repo_owners = ['aadityayadav']
    repo_tokens = []

    extraction = dataExtraction(repo_name, repo_owners, repo_tokens)

    # run any or all 4 commands below
    
    extraction.extract_general_overview()

    # extraction.extract_aggregate_metrics()

    # extraction.extract_data_commit_contributor()

    # extraction.extract_data_pr()

if __name__ == "__main__":
    main()
