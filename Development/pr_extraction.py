from pydriller import Repository
from collections import Counter
from itertools import zip_longest
from github import Github, PullRequest, PaginatedList, TimelineEvent, Issue, Auth
from datetime import datetime
import requests
import csv
import os

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


    def extract_project_metadata(self, repo_info) -> list:   
        '''
        Extracts Project Metadata from the repository using pydriller to loop over the commits
        '''
        
        repo_url = f"https://github.com/{repo_info.repo_owner}/{repo_info.repo_name}"
        first_commit_date = None
        last_commit_date = None
        project_size = 0

        for commit in Repository(repo_url).traverse_commits():
            first_commit_date = min(first_commit_date if first_commit_date is not None else commit.committer_date, commit.committer_date)
            last_commit_date = max(last_commit_date if last_commit_date is not None else commit.committer_date, commit.committer_date)
            project_size += commit.insertions - commit.deletions


        project_age = (last_commit_date - first_commit_date).days

        extracted_data = [
            project_age,
            project_size
        ]

        param_names = [
            'Project Age',
            'Project Size'
        ]
        
        print("Successfully extracted Project Meta Data.")

        return [param_names, extracted_data]
    

    def extract_commit_data_per_pr(self, repo_info, pr_number: int) -> list or None:
        '''
        Extracts commit data per pull request from the repository using the GitHub API
        '''
        # Limits 250 commits per PR which should be within range for most PRs
        total_commits = 0
        total_lines_changed = 0
        total_lines_added = 0
        total_lines_deleted = 0
        total_contributors = set()
        total_comment_count = 0
        total_files_changed = 0
        rate_of_commits = 0
        rate_of_lines_changed = 0
        rate_of_contributors = 0
        rate_of_comment_count = 0

        page_no = 0

        while True:
            page_no += 1
            base_url = f'https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/pulls/{pr_number}/commits?state=all&page={page_no}'
            headers = {'Authorization': f'token {repo_info.repo_token}'} if repo_info.repo_token is not None else {}
            headers['Accept'] = 'application/vnd.github.v3+json'

            response = requests.get(base_url, headers=headers)

            if response.status_code == 200:
                commits = response.json()
                total_commits += len(commits)

                for commit in commits:
                    total_lines_changed += commit['stats']['total'] if 'stats' in commit else 0
                    total_lines_added += commit['stats']['additions'] if 'stats' in commit else 0
                    total_lines_deleted += commit['stats']['deletions'] if 'stats' in commit else 0
                    total_contributors.add(commit['author']['login'])
                    total_comment_count += commit['commit']['comment_count']
                    total_files_changed += len(commit['files'])
            
            else:
                print("Stopping commit data extraction. Commit extraction limit reached or failed.")
                print(f"For PR: {pr_number}. On page number: {page_no}. Status code: {response.status_code}. Repo: {repo_info.repo_name}")
                break

        if total_files_changed != 0:
            rate_of_commits = total_commits / total_files_changed
            rate_of_lines_changed = total_lines_changed / total_files_changed
            rate_of_contributors = len(total_contributors) / total_files_changed
            rate_of_comment_count = total_comment_count / total_files_changed
    
        extracted_data = {
            'total_commits' : total_commits,
            'total_lines_changed' : total_lines_changed,
            'total_lines_added' : total_lines_added,
            'total_lines_deleted' : total_lines_deleted,
            'total_contributors' : len(total_contributors),
            'total_comment_count' : total_comment_count,
            'total_files_changed' : total_files_changed,
            'rate_of_commits' : rate_of_commits,
            'rate_of_lines_changed' : rate_of_lines_changed,
            'rate_of_contributors' : rate_of_contributors,
            'rate_of_comment_count' : rate_of_comment_count,
        }

        return extracted_data


    def extract_file_data_per_pr(self, repo_info, pr_number: int) -> list or None:
        '''
        Extracts file data per pull request from the repository using the GitHub API
        '''
        # Limits 3000 files per PR which should be within range for most PRs
        
        total_files_changed = 0
        total_lines_added = 0
        total_lines_deleted = 0
        total_changes = 0
        total_added_files = 0
        total_modified_files = 0
        total_removed_files = 0
        total_renamed_files = 0
        total_copied_files = 0
        rate_of_changes = 0
        rate_of_added_files = 0
        rate_of_modified_files = 0
        rate_of_removed_files = 0
        rate_of_renamed_files = 0
        rate_of_copied_files = 0

        # We have to loop over all pages to get every file
        page_no = 0

        while True:
            page_no += 1
            base_url = f'https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/pulls/{pr_number}/files?state=all&page={page_no}'
            headers = {'Authorization': f'token {repo_info.repo_token}'} if repo_info.repo_token is not None else {}
            headers['Accept'] = 'application/vnd.github.v3+json'

            response = requests.get(base_url, headers=headers)

            if response.status_code == 200:
                files = response.json()
                total_files_changed += len(files)

                for file in files:
                    total_lines_added += file['additions']
                    total_lines_deleted += file['deletions']
                    total_changes += file['changes']
                    total_added_files += int(file['status'] == 'added')
                    total_modified_files += int(file['status'] == 'modified')
                    total_removed_files += int(file['status'] == 'removed')
                    total_renamed_files += int(file['status'] == 'renamed')
                    total_copied_files += int(file['status'] == 'copied')

            else:
                print("Stopping file data extraction. File extraction limit reached or failed.")
                print(f"For PR: {pr_number}. On page number: {page_no}. Status code: {response.status_code}. Repo: {repo_info.repo_name}")
                break
            
        rate_of_changes = total_changes / total_files_changed
        rate_of_added_files = total_added_files / total_files_changed
        rate_of_modified_files = total_modified_files / total_files_changed
        rate_of_removed_files = total_removed_files / total_files_changed
        rate_of_renamed_files = total_renamed_files / total_files_changed
        rate_of_copied_files = total_copied_files / total_files_changed

        extracted_data = {
            'total_files_changed' : total_files_changed,
            'total_lines_added' : total_lines_added,
            'total_lines_deleted' : total_lines_deleted,
            'total_changes' : total_changes,
            'total_added_files' : total_added_files,
            'total_modified_files' : total_modified_files,
            'total_removed_files' : total_removed_files,
            'total_renamed_files' : total_renamed_files,
            'total_copied_files' : total_copied_files,
            'rate_of_changes' : rate_of_changes,
            'rate_of_added_files' : rate_of_added_files,
            'rate_of_modified_files' : rate_of_modified_files,
            'rate_of_removed_files' : rate_of_removed_files,
            'rate_of_renamed_files' : rate_of_renamed_files,
            'rate_of_copied_files' : rate_of_copied_files
        }

        return extracted_data


    def calculate_age(self, created_at):
        now = datetime.utcnow()
        created_at = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
        age = now - created_at
        return age.total_seconds() / 3600  # Convert to hours


    def extract_pull_request_data(self, repo_info, csv_filename: str) -> list or None:
        '''
        Extracts pull request data from the repository using the GitHub API
        '''

        # Note: we are writing in the csv file directly instead of returning the data to save system memory
        # Check if the folder exists, create it if not
        if not os.path.exists('ExtractedData'):
            os.makedirs('ExtractedData')

        file_path = os.path.join('ExtractedData', csv_filename)

        with open(file_path, 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow([
                'PR Number',
                'PR State',
                'created_at',
                'updated_at',
                'closed_at',
                'merged_at',
                'PR age',
                'Number of Labels',
                'Label Names',
                'Milestone Open Issues',
                'Milestone Closed Issues',
                'Head Repo Open Issues Count',
                'Head Repo Open Issues',
                'Base Repo Open Issues Count',
                'Base Repo Open Issues',
                'Number of Assignees',
                'Number of Requested Reviewers',
                'Number of Requested Teams',
                'Commit Frequency',
                'Average Commit Size',
                'Total Commits',
                'Total Lines Changed Based On Commits',
                'Total Lines Added Based On Commits',
                'Total Lines Deleted  Based On Commits',
                'Total Contributors Based On Commits',
                'Total Comment Count Based On Commits',
                'Total Files Changed Based On Commits',
                'Rate of Commits',
                'Rate of Lines Changed Based On Commits',
                'Rate of Contributors Based On Commits',
                'Rate of Comment Count Based On Commits',
                'Total Files Changed Based On Files',
                'Total Lines Added Based On Files',
                'Total Lines Deleted Based On Files',
                'Total Changes Based On Files',
                'Total Added Files Based On Files',
                'Total Modified Files Based On Files',
                'Total Removed Files Based On Files',
                'Total Renamed Files Based On Files',
                'Total Copied Files Based On Files',
                'Rate of Changes Based On Files',
                'Rate of Added Files Based On Files',
                'Rate of Modified Files Based On Files',
                'Rate of Removed Files Based On Files',
                'Rate of Renamed Files Based On Files',
                'Rate of Copied Files Based On Files'
            ])

            page_no = 0

            while True:
                page_no += 1
                base_url = f'https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/pulls?state=all&page={page_no}'
                
                headers = {'Authorization': f'token {repo_info.repo_token}'} if repo_info.repo_token is not None else {}
                headers['Accept'] = 'application/vnd.github.v3+json'
                
                response = requests.get(base_url, headers=headers)

                if response.status_code == 200:
                    prs = response.json()
                    
                    if len(prs) == 0:
                        break

                    for pr in prs:
                        print(f"Extracting data for PR: {pr['number']}")
                        commit_frequency = 0
                        pr_age = self.calculate_age(pr['created_at'])
                        file_data = self.extract_file_data_per_pr(repo_info, pr['number'])
                        commit_data = self.extract_commit_data_per_pr(repo_info, pr['number'])

                        commit_frequency = commit_data['total_commits'] / pr_age
                        average_commit_size = commit_data['total_lines_changed'] / file_data['total_files_changed'] if file_data['total_files_changed'] != 0 else 0
                    
                        label_names = ""
                        for label in pr['labels']:
                            label_names += label['name'] + ','

                        csv_writer.writerow([
                            pr['number'],
                            pr['state'],
                            pr['created_at'],
                            pr['updated_at'],
                            pr['closed_at'],
                            pr['merged_at'],
                            pr_age,
                            len(pr['labels']),
                            label_names,
                            pr['milestone']['open_issues'] if pr['milestone'] is not None else 0,
                            pr['milestone']['closed_issues'] if pr['milestone'] is not None else 0,
                            pr['head']['repo']['open_issues_count'],
                            pr['head']['repo']['open_issues'],
                            pr['base']['repo']['open_issues_count'],
                            pr['base']['repo']['open_issues'],
                            len(pr['assignees']),
                            len(pr['requested_reviewers']),
                            len(pr['requested_teams']),
                            commit_frequency,
                            average_commit_size,
                            commit_data['total_commits'],
                            commit_data['total_lines_changed'],
                            commit_data['total_lines_added'],
                            commit_data['total_lines_deleted'],
                            commit_data['total_contributors'],
                            commit_data['total_comment_count'],
                            commit_data['total_files_changed'],
                            commit_data['rate_of_commits'],
                            commit_data['rate_of_lines_changed'],
                            commit_data['rate_of_contributors'],
                            commit_data['rate_of_comment_count'],
                            file_data['total_files_changed'],
                            file_data['total_lines_added'],
                            file_data['total_lines_deleted'],
                            file_data['total_changes'],
                            file_data['total_added_files'],
                            file_data['total_modified_files'],
                            file_data['total_removed_files'],
                            file_data['total_renamed_files'],
                            file_data['total_copied_files'],
                            file_data['rate_of_changes'],
                            file_data['rate_of_added_files'],
                            file_data['rate_of_modified_files'],
                            file_data['rate_of_removed_files'],
                            file_data['rate_of_renamed_files'],
                            file_data['rate_of_copied_files']
                        ])
        
                else:
                    print(f"Failed to fetch Pull Requests on page: {page_no}. Status code: {response.status_code}. Repo: {repo_info.repo_name}")
                    print("Stopping Pull Request data extraction")
                    break


        print("Successfully extracted pull request data.")
    
        
    def extract_data(self):
        '''
        Extracts data from all the repository using the GitHub API and pydriller
        '''
        for repo_info in self.repo_infos:
            print(f"Extracting data for repo: {repo_info.repo_name}")

            csv_filename = repo_info.repo_owner + '_' + repo_info.repo_name + '.csv'

            print(f"PR data is stored in the following file: {csv_filename}")
            
            # print("Extracting Project Metadata...")
            # project_metadata = self.extract_project_metadata(repo_info)
            # print("Printing Project Metadata:")
            # print("")
            # print(project_metadata)
            # print("")

            print("Extracting pull request data...")
            self.extract_pull_request_data(repo_info, csv_filename)
            print("")

            print("Extraction Complete.")
            print("")
            

def main():
    # Example usage (list all repo names, owner and tokens in the same order)
    # repo_names = ["pydriller"]
    # repo_owners = ["ishepard"]
    repo_names = ["spotify-web-api-wrapper"]
    repo_owners = ["jzheng2017"]

    # Add GitHub tokens if available for authentication and avoiding rate limiting by the GitHub API

    dataExtraction(repo_names,repo_owners).extract_data()

if __name__ == "__main__":
    main()