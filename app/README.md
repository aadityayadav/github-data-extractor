## Introduction
A Python package to extract GitHub repository insights including commit history, pull request analysis, contributor trends, and overall repository health. Designed to simplify engineering reporting and performance tracking.
<br>
<br>
<br>

## Requirements
- Python 3.5 or later
- [Google Maps API Key](https://developers.google.com/maps/documentation/embed/get-api-key)
<br>
<br>


## Installation
```
pip install github-data-extractor
```
<br>
<br>


## Usage and Documentation
This example shows how to use the geocentroid package.
```
from github_data_extractor import dataExtraction
from dotenv import load_dotenv
import os

load_dotenv()
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

def main():
    repo_name = ['translate_lib']
    repo_owners = ['aadityayadav']
    repo_tokens = [GITHUB_TOKEN]

    extraction = dataExtraction(repo_name, repo_owners, repo_tokens)

    # method 1    
    extraction.extract_general_overview()
    # method 2
    extraction.extract_aggregate_metrics()
    # method 3
    extraction.extract_data_commit_contributor()
    # method 4
    extraction.extract_data_pr()

if __name__ == "__main__":
    main()
```

> All functions take no parameters directly.  
> You must provide `repo_name`, `repo_owners`, and `repo_tokens` as **lists**, so you can extract data from multiple repositories at once.
<br>  

### 1) `extract_general_overview()`  
Fetches a high-level snapshot of the repository:
- Branch information (total branches, last updated)
- Linked vs unlinked issues
- File data associated with each pull request  
<br>  

### 2) `extract_aggregate_metrics()`  
Provides an overview of project health using aggregated statistics:
- Commit activity over time
- File modification frequency
- Pull request volume and lifecycle
- Pull request quality: reviews, size, and merge times  
<br>  

### 3) `extract_data_commit_contributor()`  
Gathers contributor and commit behavior:
- Commit counts by contributor
- Time-based commit activity
- New vs returning contributor patterns  
<br>  

### 4) `extract_data_pr()`  
Detailed pull request analytics:
- PR open/merge/close timestamps
- Review histories and discussions
- Issue linkages, milestone tagging, and contributor-level PR trends  
<br>  
<br>  

**Returns:**
- Automatically saves a CSV under a folder `ExtractedData` containing repo metrics.
<br>  
