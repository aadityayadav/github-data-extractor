from pydriller import Repository
from collections import Counter
from itertools import zip_longest
from github import Github, PullRequest, PaginatedList, TimelineEvent, Issue, Auth
from datetime import datetime
import requests
import time
import csv
import os
from dotenv import load_dotenv
import os

load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

class repoInfo:
    def __init__(self, repo_name: str, repo_owner: str, repo_token: str = None):
        self.repo_name = repo_name
        self.repo_owner = repo_owner
        self.repo_token = repo_token
        self.token_index = 0

class dataExtraction:
    def __init__(self, repo_names: list, repo_owners: list, repo_tokens: list = []):
        '''
        Initializes the repo_info list with the repo names, owners and tokens
        '''
        zipped_data = zip_longest(repo_names, repo_owners, repo_tokens, fillvalue=None)
        self.repo_infos = [repoInfo(url, owner, token) for url, owner, token in zipped_data]

        self.tokens = repo_tokens
        self.token_index = 0

        # GitHub Rate Limit URL
        self.rate_limit_url = "https://api.github.com/rate_limit"

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

        # Detailed contributor activity
        detailed_contributor_activity = [
            {'Contributor': contributor, 'Commits': commits} for contributor, commits in contributors.items()
        ]

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
            top_contributors,
            detailed_contributor_activity
        ]

        param_names = [
            'Project Age',
            'Project Size',
            'Churn Rate Over Time Based on Time',
            'Churn Rate Over Time Based on Commits',
            'Total Number of Commits',
            'Commit Frequency',
            'Average Commit Size',
            'Average Code Complexity',
            'Total Number of Contributors',
            'Top Contributors',
            'Detailed Contributor Activity'
        ]
        
        return [param_names, extracted_data]

    def get_headers(self):
        token = self.tokens[self.token_index]
        return {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }

    def switch_token(self):
        self.token_index = (self.token_index + 1) % len(self.tokens)

    def handle_rate_limit(self):
        '''Handles API rate limits with backoff and token switching.'''
        while True:
            headers = self.get_headers()
            response = requests.get(self.rate_limit_url, headers=headers)

            if response.status_code == 200:
                rate_limit = response.json()
                remaining = rate_limit['rate']['remaining']
                reset_time = rate_limit['rate']['reset']

                if remaining > 0:
                    break  # Enough quota, continue
                else:
                    wait_time = reset_time - time.time()
                    print(f"Rate limit exceeded. Waiting {wait_time:.2f} seconds...")
                    time.sleep(wait_time + 1)  # Wait for reset
                    self.switch_token()  # Switch to next token
            else:
                print("Error fetching rate limit. Retrying...")
                time.sleep(10)

    def extract_commit_data_per_pr(self, repo_info, pr_number: int) -> list or None:
        '''
        Extracts commit data per pull request from the repository using the GitHub API.
        '''
        # Initialize counters and metrics
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
        headers = self.get_headers()


        github_object = Github() if repo_info.repo_token is None else Github(auth=Auth.Token(repo_info.repo_token))
        repo = github_object.get_repo(f"{repo_info.repo_owner}/{repo_info.repo_name}")
        pr_list = repo.get_pulls(state='all')
        
        page_no = 0

        for pr in pr_list:
            pr_number = pr.number

        while True:
            self.handle_rate_limit()
            page_no += 1
            base_url = f'https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/pulls/{pr_number}/commits?state=all&page={page_no}'

            response = requests.get(base_url, headers=headers)

            if response.status_code == 200:
                commits = response.json()

                if not commits:
                    break

                total_commits += len(commits)

                for commit in commits:
                    # Handle rate limits before fetching detailed commit data
                    self.handle_rate_limit()

                    # Fetch detailed commit data to get 'files'
                    commit_details_url = f"https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/commits/{commit['sha']}"
                    details_response = requests.get(commit_details_url, headers=headers)

                    if details_response.status_code == 200:
                        commit_details = details_response.json()

                        # Extract file change details if present
                        total_files_changed += len(commit_details.get('files', []))

                        # Extract lines changed
                        stats = commit_details.get('stats', {})
                        total_lines_changed += stats.get('total', 0)
                        total_lines_added += stats.get('additions', 0)
                        total_lines_deleted += stats.get('deletions', 0)

                        # Extract contributors
                        author = commit.get('author')
                        if author and 'login' in author:
                            total_contributors.add(author['login'])

                        # Extract comment count
                        total_comment_count += commit['commit'].get('comment_count', 0)

                    else:
                        print(f"Failed to fetch commit details for SHA: {commit['sha']} in PR: {pr_number}")

            elif response.status_code == 403:
                print(f"Forbidden error for PR: {pr_number}, Repo: {repo_info.repo_name}. Check your token and permissions.")
                break

            else:
                # Stop extraction on error
                print("Stopping commit data extraction. Commit extraction limit reached or failed.")
                print(f"For PR: {pr_number}. On page number: {page_no}. Status code: {response.status_code}. Repo: {repo_info.repo_name}")
                break

        # Calculate rates
        if total_files_changed > 0:
            rate_of_commits = total_commits / total_files_changed
            rate_of_lines_changed = total_lines_changed / total_files_changed
            rate_of_contributors = len(total_contributors) / total_files_changed
            rate_of_comment_count = total_comment_count / total_files_changed
        else:
            rate_of_commits = 0
            rate_of_lines_changed = 0
            rate_of_contributors = 0
            rate_of_comment_count = 0

        # Parameter names and extracted data
        param_names = [
            'Total Commits',
            'Total Lines Changed',
            'Total Lines Added',
            'Total Lines Deleted',
            'Total Contributors',
            'Total Comment Count',
            'Total Files Changed',
            'Rate of Commits',
            'Rate of Lines Changes',
            'Rate of Contributors',
            'Rate of Comment Count'
        ]

        extracted_data = [
            total_commits,
            total_lines_changed,
            total_lines_added,
            total_lines_deleted,
            len(total_contributors),
            total_comment_count,
            total_files_changed,
            rate_of_commits,
            rate_of_lines_changed,
            rate_of_contributors,
            rate_of_comment_count,
        ]

        return [param_names, extracted_data]

    def extract_file_data_per_pr(self, repo_info, pr_number: int) -> list or []:
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
            
        if total_files_changed > 0:
            rate_of_changes = total_changes / total_files_changed
            rate_of_added_files = total_added_files / total_files_changed
            rate_of_modified_files = total_modified_files / total_files_changed
            rate_of_removed_files = total_removed_files / total_files_changed
            rate_of_renamed_files = total_renamed_files / total_files_changed
            rate_of_copied_files = total_copied_files / total_files_changed
        elif total_files_changed == 0:
            print(f"No files found in PR: {pr_number}. Skipping file data extraction.")
            return None
        else:
            rate_of_changes = 0
            rate_of_added_files = 0
            rate_of_modified_files = 0
            rate_of_removed_files = 0
            rate_of_renamed_files = 0
            rate_of_copied_files = 0

        param_names = [
            'Total Files Changes',
            'Total Lines Added',
            'Total Lines Deleted',
            'Total Changes',
            'Total Added Files',
            'Total Modified Files',
            'Total Removed Files',
            'Total Renamed Files',
            'Total Copied Files',
            'Rate of Changes',
            'Rate of Added Files',
            'Rate of Modified Files',
            'Rate of Removed Files',
            'Rate of Renamed Files',
            'Rate of Copied Files'
        ]

        extracted_data = [
            total_files_changed,
            total_lines_added,
            total_lines_deleted,
            total_changes,
            total_added_files,
            total_modified_files,
            total_removed_files,
            total_renamed_files,
            total_copied_files,
            rate_of_changes,
            rate_of_added_files,
            rate_of_modified_files,
            rate_of_removed_files,
            rate_of_renamed_files,
            rate_of_copied_files
        ]

        return [param_names, extracted_data]

    def calculate_age(self, created_at):
        now = datetime.utcnow()
        created_at = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
        age = now - created_at
        return age.total_seconds() / 3600


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

            #headers = {'Authorization': f'token {repo_info.repo_token}'} if repo_info.repo_token is not None else {}
            headers = {
                'Authorization': f'token {repo_info.repo_token}',
                'Accept': 'application/vnd.github.v3+json'
            }

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

                        commit_frequency = commit_data[1]['total_commits'] / pr_age
                        average_commit_size = commit_data[1][['total_lines_changed']] / file_data[1][0] if file_data[1][0] != 0 else 0
                    
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
                            commit_data[1]['total_commits'],
                            commit_data[1]['total_lines_changed'],
                            commit_data[1]['total_lines_added'],
                            commit_data[1]['total_lines_deleted'],
                            commit_data[1]['total_contributors'],
                            commit_data[1]['total_comment_count'],
                            commit_data[1]['total_files_changed'],
                            commit_data[1]['rate_of_commits'],
                            commit_data[1]['rate_of_lines_changed'],
                            commit_data[1]['rate_of_contributors'],
                            commit_data[1]['rate_of_comment_count'],
                            file_data[1][0],
                            file_data[1][1],
                            file_data[1][2],
                            file_data[1][3],
                            file_data[1][4],
                            file_data[1][5],
                            file_data[1][6],
                            file_data[1][7],
                            file_data[1][8],
                            file_data[1][9],
                            file_data[1][10],
                            file_data[1][11], 
                            file_data[1][12],
                            file_data[1][13], 
                            file_data[1][14]

                        ])
        
                else:
                    print(f"Failed to fetch Pull Requests on page: {page_no}. Status code: {response.status_code}. Repo: {repo_info.repo_name}")
                    print("Stopping Pull Request data extraction")
                    break


        print("Successfully extracted pull request data.")

    def extract_branch_data(self, repo_info) -> list or None:
        '''
        Extracts branch data from the repository using PyGithub
        '''
        github_object = Github() if repo_info.repo_token is None else Github(auth = Auth.Token(repo_info.repo_token))

        repo = github_object.get_repo(f"{repo_info.repo_owner}/{repo_info.repo_name}")
        branches = list(repo.get_branches())

        extracted_data = [
            len(branches),
            [branch.name for branch in branches]
        ]

        param_names = [
            'Number of Current Branches',
            'Current Branch Names'
        ]

        print("Successfully extracted branch data.")

        return [param_names, extracted_data]
    
    def get_linked_issue_from_pr(self, pr: PullRequest) -> Issue or None:
        '''
        Check if the given pr has a linked issue.
        '''
        events_pages: PaginatedList[TimelineEvent] = pr.as_issue().get_timeline()
        pg_num = 0
        while events_pages.get_page(pg_num):
            page = events_pages.get_page(pg_num)
            pg_num += 1
            for e in page:
                if str(e.event) == 'cross-referenced':
                    if e.source and e.source.issue:
                        return e.source.issue
        
        return None
    
    def calculate_pr_quality(self, repo_info, total_prs: int, pr_numbers: list) -> dict:
        '''
        Calculates PR quality based on various metrics such as reviews, merge time and code churn.
        '''
        github_object = Github() if repo_info.repo_token is None else Github(auth=Auth.Token(repo_info.repo_token))
        repo = github_object.get_repo(f"{repo_info.repo_owner}/{repo_info.repo_name}")

        prs_with_issues = 0
        total_reviews = 0
        total_review_comments = 0
        total_merge_time = 0
        long_open_prs = 0
        total_participants = 0
        reverted_prs = 0
        pr_with_tests_added = 0
        total_churn = 0

        for pr_number in pr_numbers:
            pr: PullRequest = repo.get_pull(number=pr_number)
            issue_linked_to_pr = self.get_linked_issue_from_pr(pr)
            if issue_linked_to_pr is not None:
                prs_with_issues += 1

            # Review Metrics
            reviews = pr.get_reviews()
            total_reviews += reviews.totalCount
            total_review_comments += sum(review.body.count('\n') for review in reviews)

            # Merge Time
            if pr.merged_at and pr.created_at:
                merge_time = (pr.merged_at - pr.created_at).total_seconds()
                total_merge_time += merge_time
                if merge_time > 30 * 24 * 3600:  # PR open for over 30 days
                    long_open_prs += 1

            # Engagement Metrics
            participants = len(set([comment.user.login for comment in pr.get_comments()]))
            total_participants += participants

            # Reverted PRs
            if pr.title.lower().startswith('revert'):
                reverted_prs += 1

            # Testing Metrics
            if 'test' in pr.changed_files.lower():  
                pr_with_tests_added += 1

            # Churn Metrics
            total_churn += pr.additions + pr.deletions

        # Aggregating Metrics
        pr_quality_metrics = {
            'Linked Issues Percentage': prs_with_issues / total_prs,
            'Average Reviews per PR': total_reviews / total_prs,
            'Average Review Comments per PR': total_review_comments / total_reviews if total_reviews else 0,
            'Average Merge Time (seconds)': total_merge_time / total_prs,
            'Long-Open PRs Percentage': long_open_prs / total_prs,
            'Average Participants per PR': total_participants / total_prs,
            'Reverted PRs Percentage': reverted_prs / total_prs,
            'PRs with Test Coverage Additions': pr_with_tests_added / total_prs,
            'Average Code Churn per PR': total_churn / total_prs,
        }

        return pr_quality_metrics

    
    def extract_data_commit_contributor(self, pr_number: int):
        '''
        Extracts commit and contributor data from all the repository using the GitHub API and pydriller
        '''
        for repo_info in self.repo_infos:
            csv_filename = repo_info.repo_owner + '_' + repo_info.repo_name + '.csv'
            
            param_names = []
            extracted_data = []
            
            commit_and_contributor_data = self.extract_commit_and_contributor_data(repo_info)
            pr_data = self.extract_commit_data_per_pr(repo_info, pr_number)

            param_names = commit_and_contributor_data[0] + pr_data[0]
            extracted_data = commit_and_contributor_data[1] + pr_data[1]

        self.write_to_csv_and_save([param_names, extracted_data], csv_filename, 'ExtractedData')

    def extract_general_overview(self, repo_info, pr_number: int):
        '''
        Extracts a general overview of the repository like file data, issue tracking data, linked issue with PRs, and branch data
        '''

        for repo_info in self.repo_infos:
            csv_filename = repo_info.repo_owner + '_' + repo_info.repo_name + '.csv'

            param_names = []
            extracted_data = []

            file_data_per_pr = self.extract_file_data_per_pr(repo_info, pr_number)
            #issue_tracking_data = self.extract_issue_tracking_data(repo_info)
            branch_data = self.extract_branch_data(repo_info)


            # param_names = file_data_per_pr[0] + issue_tracking_data[0] + branch_data[0]
            # extracted_data = file_data_per_pr[1] + issue_tracking_data[1] + branch_data[1]

            param_names = file_data_per_pr[0] + branch_data[0]
            extracted_data = file_data_per_pr[1] + branch_data[1]

            github_object = Github() if repo_info.repo_token is None else Github(auth=Auth.Token(repo_info.repo_token))
            repo = github_object.get_repo(f"{repo_info.repo_owner}/{repo_info.repo_name}")
            pr = repo.get_pull(pr_number)

            linked_issue = self.get_linked_issue_from_pr(pr)

            if linked_issue:
                linked_issue_data = [
                    linked_issue.number,
                    linked_issue.state,
                    linked_issue.title,
                    linked_issue.created_at,
                    linked_issue.updated_at,
                    linked_issue.closed_at,
                    [label.name for label in linked_issue.labels],
                    linked_issue.comments,
                ]

                linked_issue_params = [
                    'linked_issue_number',
                    'linked_issue_state',
                    'linked_issue_title',
                    'linked_issue_created_at',
                    'linked_issue_updated_at',
                    'linked_issue_closed_at',
                    'linked_issue_labels',
                    'linked_issue_comments',
                ]

            else:
                linked_issue_data = [None] * 8
                linked_issue_params = [
                    'linked_issue_number',
                    'linked_issue_state',
                    'linked_issue_title',
                    'linked_issue_created_at',
                    'linked_issue_updated_at',
                    'linked_issue_closed_at',
                    'linked_issue_labels',
                    'linked_issue_comments',
                ]

                param_names += linked_issue_params
                extracted_data += linked_issue_data

        self.write_to_csv_and_save([param_names, extracted_data], csv_filename, 'ExtractedData')



    def extract_data_pr(self):
        '''
        Extracts PR data from all repository using Github API and pydriller
        '''
        for repo_info in self.repo_infos:
            print(f"Extracting data for repo: {repo_info.repo_name}")
            csv_filename = repo_info.repo_owner + '_' + repo_info.repo_name + '.csv'
            print(f"PR data is stored in the following file: {csv_filename}")
            print("Extracting pull request data...")
            self.extract_pull_request_data(repo_info, csv_filename)
            print("")

            print("Extraction Complete.")
            print("")

def main():
    repo_name = ['geo-centroid']
    repo_owners = ['aadityayadav']
    repo_tokens = [GITHUB_TOKEN]
    pr_number = 1

    extraction = dataExtraction(repo_name, repo_owners, repo_tokens)

    # for repo_info in extraction.repo_infos:
    #     extraction.extract_general_overview(repo_info, pr_number)

    extraction.extract_data_commit_contributor(pr_number)

    extraction.extract_data_pr()


if __name__ == "__main__":
    main()