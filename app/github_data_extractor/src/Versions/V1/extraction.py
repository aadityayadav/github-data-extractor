from pydriller import Repository
from collections import Counter
from itertools import zip_longest
import requests
import csv
import os

#dataclass
class repoInfo:
    def __init__(self, repo_name: str, repo_owner: str, repo_token: str = None):
        self.repo_name = repo_name
        self.repo_owner = repo_owner
        self.repo_token = repo_token

class dataExtraction:
    def __init__(self, repo_names: list, repo_owners: list, repo_tokens: list = []):
        '''
        Initializes the repo_info list with the repo names, owners and tokens
        '''
        zipped_data = zip_longest(repo_names, repo_owners, repo_tokens, fillvalue=None)
        self.repo_infos = [repoInfo(url, owner, token) for url, owner, token in zipped_data]


    def write_to_csv_and_save(self, data: list, file_name: str, folder_path: str):
        '''
        Writes the data to a csv file and saves it to the specified folder
        '''
        # Check if the folder exists, create it if not
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        file_path = os.path.join(folder_path, file_name)

        with open(file_path, 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerows(data)

        print(f'Data written to {file_path} successfully.')

    def extract_commit_and_contributor_data(self, repo_info) -> list:   
        '''
        Extracts commit and contributor data from the repository using pydriller to loop over the commits
        '''
        
        repo_url = f"https://github.com/{repo_info.repo_owner}/{repo_info.repo_name}"
        total_number_of_commits = 0
        total_lines_changed = 0
        first_commit_date = None
        last_commit_date = None
        project_size = 0
        code_complexity = 0
        contributors = Counter()

        for commit in Repository(repo_url).traverse_commits():
            total_number_of_commits += 1
            total_lines_changed += commit.lines
            first_commit_date = min(first_commit_date if first_commit_date is not None else commit.committer_date, commit.committer_date)
            last_commit_date = max(last_commit_date if last_commit_date is not None else commit.committer_date, commit.committer_date)
            project_size += commit.insertions - commit.deletions
            code_complexity += commit.dmm_unit_complexity if commit.dmm_unit_complexity is not None else 0
            contributors[commit.author.name] = contributors.get(commit.author.name, 0) + 1


        project_age = (last_commit_date - first_commit_date).days
        commit_frequency = total_number_of_commits / (project_age + 1) 
        avg_commit_size = total_lines_changed / total_number_of_commits
        avg_code_complexity = code_complexity / total_number_of_commits
        total_number_of_contributors = len(contributors)
        top_contributors = contributors.most_common(5)

        # dict
        extracted_data = [
            project_age,
            project_size,
            project_size/project_age,
            project_size/total_number_of_commits,
            total_number_of_commits,
            commit_frequency,
            avg_commit_size,
            avg_code_complexity,
            total_number_of_contributors,
            top_contributors
        ]

        param_names = [
            'Project Age',
            'Project Size',
            'Churn Rate Based on Time',
            'Churn Rate Based on Commits',
            'Total Number of Commits',
            'Commit Frequency',
            'Average Commit Size',
            'Average Code Complexity',
            'Total Number of Contributors',
            'Top Contributors'
        ]
        
        return [param_names, extracted_data]

    def extract_issue_tracking_data(self, repo_info) -> list or None:
        '''
        Extracts issue tracking data from the repository using the GitHub API
        '''
        page_no = 1
        open_issues = 0
        closed_issues = 0
        updated_issues = 0
        total_issues = 0
        issue_categories = set()

        while True:
            base_url = f'https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/issues?state=all&page={page_no}'
            page_no += 1

            headers = {'Authorization': f'token {repo_info.repo_token}'} if repo_info.repo_token is not None else {}

            response = requests.get(base_url, headers=headers)

            if response.status_code == 200:
                issues = response.json()
                if len(issues) == 0:
                    break
                
                total_issues += len(issues)
                
                for issue in issues:
                    if issue['state'] == 'open':
                        open_issues += 1
                    elif issue['state'] == 'closed':
                        closed_issues += 1
                    
                    if issue['updated_at'] is not None and issue['updated_at'] > issue['created_at']:
                        updated_issues += 1

                if 'labels' in issue and issue['labels']:
                    issue_categories.update(label['name'] for label in issue['labels'])
                
            else:
                print(f"Failed to fetch issues on page: {page_no}. Status code: {response.status_code}. Repo: {repo_info.repo_name}")
                break
 
        if total_issues == 0:
            total_issues = 1
        
        extracted_data = [
            open_issues, 
            open_issues/total_issues, 
            closed_issues/total_issues, 
            updated_issues/total_issues, 
            issue_categories
        ]

        param_names = [
            'Open Issues',
            'Open Issues Ratio',
            'Closed Issues Ratio',
            'Updated Issues Ratio',
            'Issue Categories'
        ]

        return [param_names, extracted_data]
    
    def extract_pull_request_data(self, repo_info) -> list or None:
        '''
        Extracts pull request data from the repository using the GitHub API
        '''

        page_no = 1
        open_prs = 0
        closed_prs = 0
        merged_prs = 0
        total_prs = 0

        while True:
            base_url = f'https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/pulls?state=all&page={page_no}'
            page_no += 1
            
            headers = {'Authorization': f'token {repo_info.repo_token}'} if repo_info.repo_token is not None else {}
            headers['Accept'] = 'application/vnd.github.v3+json'
            
            response = requests.get(base_url, headers=headers)

            if response.status_code == 200:
                prs = response.json()
                
                if len(prs) == 0:
                    break

                total_prs += len(prs) 

                for pr in prs:
                    if pr['state'] == 'open':
                        open_prs += 1
                    elif pr['state'] == 'closed':
                        closed_prs += 1
                    elif pr['merged_at'] is not None:
                        merged_prs += 1

    
            else:
                print(f"Failed to fetch Pull Requests on page: {page_no}. Status code: {response.status_code}. Repo: {repo_info.repo_name}")
                break
            
            if total_prs == 0:
                total_prs = 1

            extracted_data = [
                open_prs, 
                open_prs/total_prs, 
                closed_prs/total_prs, 
                merged_prs/total_prs
            ]

            param_names = [
                'Open PRs',
                'Open PRs Ratio',
                'Closed PRs Ratio',
                'Merged PRs Ratio'
            ]

            return [param_names, extracted_data]
    
    def extract_data(self):
        '''
        Extracts data from all the repository using the GitHub API and pydriller
        '''
        for repo_info in self.repo_infos:
            csv_filename = repo_info.repo_owner + '_' + repo_info.repo_name + '.csv'
            
            param_names = []
            extracted_data = []
            
            commit_and_contributor_data = self.extract_commit_and_contributor_data(repo_info)
            issue_tracking_data = self.extract_issue_tracking_data(repo_info)
            pull_request_data = self.extract_pull_request_data(repo_info)

            param_names = commit_and_contributor_data[0] + issue_tracking_data[0] + pull_request_data[0]
            extracted_data = commit_and_contributor_data[1] + issue_tracking_data[1] + pull_request_data[1]

            self.write_to_csv_and_save([param_names, extracted_data], csv_filename, 'ExtractedData')
            

def main():
    # Example usage (list all repo names, owner and tokens in the same order)
    repo_names = ["pydriller"]
    repo_owners = ["ishepard"]

    # Add GitHub tokens if available for authentication and avoiding rate limiting by the GitHub API

    dataExtraction(repo_names,repo_owners).extract_data()

if __name__ == "__main__":
    main()