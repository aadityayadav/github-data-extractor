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
from github.GithubException import UnknownObjectException

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

        # list
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
                    break
                else:
                    wait_time = reset_time - time.time()
                    print(f"Rate limit exceeded. Waiting {wait_time:.2f} seconds...")
                    time.sleep(wait_time + 1)
                    self.switch_token()
            else:
                print("Error fetching rate limit. Retrying...")
                time.sleep(10)

    def extract_commit_data_per_pr(self, repo_info) -> list:
        """
        Extracts commit data for all pull requests in the repository using the GitHub API.
        """
        all_data = [[
            'PR Number',
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
        ]]

        page_no = 0
        headers = {'Authorization': f'token {repo_info.repo_token}'} if repo_info.repo_token else {}
        headers['Accept'] = 'application/vnd.github.v3+json'

        while True:
            page_no += 1
            base_url = f'https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/pulls?state=all&sort=created&direction=asc&page={page_no}'
            response = requests.get(base_url, headers=headers)

            if response.status_code != 200:
                print(f"Failed to fetch PRs. Status: {response.status_code}")
                break

            prs = response.json()
            if not prs:  # No more PRs
                break

            for pr in prs:
                try:
                    pr_number = pr['number']
                    print(f"Processing PR #{pr_number}...")

                    # Initialize counters
                    total_commits = 0
                    total_lines_changed = 0
                    total_lines_added = 0
                    total_lines_deleted = 0
                    total_contributors = set()
                    total_comment_count = 0
                    total_files_changed = 0

                    # Fetch commit data for the PR
                    commit_page_no = 0
                    while True:
                        commit_page_no += 1
                        commit_url = f"https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/pulls/{pr_number}/commits?page={commit_page_no}"
                        commit_response = requests.get(commit_url, headers=headers)

                        if commit_response.status_code != 200:
                            print(f"Failed to fetch commits for PR #{pr_number}. Status: {commit_response.status_code}")
                            break

                        commits = commit_response.json()
                        if not commits:
                            break

                        total_commits += len(commits)

                        for commit in commits:
                            # Fetch commit details
                            commit_sha = commit['sha']
                            details_url = f"https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/commits/{commit_sha}"
                            details_response = requests.get(details_url, headers=headers)

                            if details_response.status_code == 200:
                                details = details_response.json()
                                total_files_changed += len(details.get('files', []))

                                stats = details.get('stats', {})
                                total_lines_changed += stats.get('total', 0)
                                total_lines_added += stats.get('additions', 0)
                                total_lines_deleted += stats.get('deletions', 0)

                                author = commit.get('author')
                                if author and 'login' in author:
                                    total_contributors.add(author['login'])

                                total_comment_count += commit['commit'].get('comment_count', 0)

                    # Calculate rates
                    rate_of_commits = total_commits / total_files_changed if total_files_changed > 0 else 0
                    rate_of_lines_changed = total_lines_changed / total_files_changed if total_files_changed > 0 else 0
                    rate_of_contributors = len(total_contributors) / total_files_changed if total_files_changed > 0 else 0
                    rate_of_comment_count = total_comment_count / total_files_changed if total_files_changed > 0 else 0

                    # Append data row
                    all_data.append([
                        pr_number,
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
                        rate_of_comment_count
                    ])

                except Exception as e:
                    print(f"Error processing PR {pr['number']}: {e}")

        return all_data


    def extract_file_data_per_pr(self, repo_info) -> list:
        '''
        Extracts file data for all pull requests using the GitHub API.
        '''
        # Add headers
        all_file_data = [[
            'PR Number',
            'Total Files Changed',
            'Total Lines Added',
            'Total Lines Deleted',
            'Total Changes',
            'Total Added Files',
            'Total Modified Files',
            'Total Removed Files',
            'Total Renamed Files',
            'Total Copied Files'
        ]]

        page_no = 0
        while True:
            page_no += 1
            base_url = f'https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/pulls?state=all&sort=created&direction=asc&page={page_no}'
            headers = {'Authorization': f'token {repo_info.repo_token}'} if repo_info.repo_token else {}
            headers['Accept'] = 'application/vnd.github.v3+json'

            response = requests.get(base_url, headers=headers)
            if response.status_code != 200:
                print(f"Failed to fetch PRs. Status code: {response.status_code}")
                break

            prs = response.json()
            if not prs:
                break

            for pr in prs:
                try:
                    pr_number = pr['number']
                    print(f"Processing files for PR: {pr_number}")

                    # Initialize counters
                    total_files_changed = 0
                    total_lines_added = 0
                    total_lines_deleted = 0
                    total_changes = 0
                    total_added_files = 0
                    total_modified_files = 0
                    total_removed_files = 0
                    total_renamed_files = 0
                    total_copied_files = 0

                    file_page_no = 0
                    while True:
                        file_page_no += 1
                        file_url = f'https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/pulls/{pr_number}/files?page={file_page_no}'
                        file_response = requests.get(file_url, headers=headers)

                        if file_response.status_code != 200:
                            break

                        files = file_response.json()
                        if not files:
                            break

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

                    # Append row data
                    all_file_data.append([
                        pr_number,
                        total_files_changed,
                        total_lines_added,
                        total_lines_deleted,
                        total_changes,
                        total_added_files,
                        total_modified_files,
                        total_removed_files,
                        total_renamed_files,
                        total_copied_files
                    ])

                except Exception as e:
                    print(f"Error processing files for PR {pr_number}: {e}")

        return all_file_data

    def calculate_age(self, created_at):
        now = datetime.utcnow()
        created_at = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
        age = now - created_at
        return age.total_seconds() / 3600

    def calculate_pr_quality(self, repo_info) -> list:
        """
        Calculates PR quality for all pull requests using the GitHub API.
        """
        # Add headers
        all_pr_quality_data = [[
            "PR Number",
            "Total Reviews",
            "Total Review Comments",
            "Merge Time (seconds)",
            "Long-Open PR",
            "Participants",
            "Reverted PR",
            "Test Coverage Additions",
            "Code Churn"
        ]]

        page_no = 0
        while True:
            page_no += 1
            base_url = f'https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/pulls?state=all&sort=created&direction=asc&page={page_no}'
            headers = {'Authorization': f'token {repo_info.repo_token}'} if repo_info.repo_token else {}
            headers['Accept'] = 'application/vnd.github.v3+json'

            response = requests.get(base_url, headers=headers)
            if response.status_code != 200:
                print(f"Failed to fetch PRs. Status code: {response.status_code}")
                break

            prs = response.json()
            if not prs:
                break

            for pr in prs:
                try:
                    pr_number = pr['number']
                    print(f"Processing quality metrics for PR: {pr_number}")

                    # Initialize counters
                    total_reviews = 0
                    total_review_comments = 0
                    merge_time = 0
                    long_open_pr = 0
                    participants = 0
                    reverted_pr = 0
                    test_coverage_added = 0
                    churn = 0

                    # Fetch detailed PR data
                    pr_url = f"https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/pulls/{pr_number}"
                    pr_response = requests.get(pr_url, headers=headers)
                    if pr_response.status_code != 200:
                        print(f"Failed to fetch details for PR {pr_number}. Skipping.")
                        continue
                    pr_details = pr_response.json()

                    # Reviews
                    reviews_url = f"{pr_url}/reviews"
                    reviews_response = requests.get(reviews_url, headers=headers)
                    if reviews_response.status_code == 200:
                        reviews = reviews_response.json()
                        total_reviews += len(reviews)
                        total_review_comments += sum(review['body'].count('\n') for review in reviews if 'body' in review)

                    # Merge Time
                    if pr_details.get('merged_at') and pr_details.get('created_at'):
                        created_at = datetime.strptime(pr_details['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                        merged_at = datetime.strptime(pr_details['merged_at'], '%Y-%m-%dT%H:%M:%SZ')
                        merge_time = (merged_at - created_at).total_seconds()
                        if merge_time > 30 * 24 * 3600:  # PR open for over 30 days
                            long_open_pr += 1

                    # Participants
                    comments_url = f"{pr_url}/comments"
                    comments_response = requests.get(comments_url, headers=headers)
                    if comments_response.status_code == 200:
                        comments = comments_response.json()
                        participants = len(set(comment['user']['login'] for comment in comments if 'user' in comment))

                    # Reverted PR
                    if pr_details['title'].lower().startswith('revert'):
                        reverted_pr += 1

                    # Test Coverage Additions
                    files_url = f"{pr_url}/files"
                    files_response = requests.get(files_url, headers=headers)
                    if files_response.status_code == 200:
                        files = files_response.json()
                        if any('test' in file['filename'].lower() for file in files):
                            test_coverage_added += 1

                    # Code Churn
                    churn = pr_details.get('additions', 0) + pr_details.get('deletions', 0)
                    # Append row data
                    all_pr_quality_data.append([
                        pr_number,
                        total_reviews,
                        total_review_comments,
                        merge_time,
                        long_open_pr,
                        participants,
                        reverted_pr,
                        test_coverage_added,
                        churn
                    ])

                except Exception as e:
                    print(f"Error processing quality metrics for PR {pr_number}: {e}")

        return all_pr_quality_data


    def extract_issue_tracking_data(self, repo_info) -> list:
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
            base_url = f'https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/issues?state=all&sort=created&direction=asc&page={page_no}'
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
     
    def extract_pull_request_data(self, repo_info, csv_filename: str, to_return: bool) -> list or None:
        '''
        Extracts pull request data from the repository using the GitHub API
        '''
        if not os.path.exists('ExtractedData'):
            os.makedirs('ExtractedData')

        file_path = os.path.join('ExtractedData', csv_filename)
        aggregated_results = []

        with open(file_path, 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)

            pr_headers = [
                'PR Number', 'PR State', 'created_at', 'updated_at', 'closed_at', 'merged_at',
                'PR age', 'Number of Labels', 'Label Names', 'Milestone Open Issues',
                'Milestone Closed Issues', 'Head Repo Open Issues Count', 'Head Repo Open Issues',
                'Base Repo Open Issues Count', 'Base Repo Open Issues', 'Number of Assignees',
                'Number of Requested Reviewers', 'Number of Requested Teams'
            ]

            commit_data = self.extract_commit_data_per_pr(repo_info)
            file_data = self.extract_file_data_per_pr(repo_info)

            commit_headers, commit_rows = commit_data[0], commit_data[1:]
            file_headers, file_rows = file_data[0], file_data[1:]

            duplicate_fields = {'Total Files Changed', 'Total Lines Added', 'Total Lines Deleted'}

            filtered_file_indices = [i for i, h in enumerate(file_headers) if h not in duplicate_fields or i == 0]
            filtered_file_headers = [file_headers[i] for i in filtered_file_indices]
            filtered_file_rows = [[row[i] for i in filtered_file_indices] for row in file_rows]

            combined_headers = pr_headers + commit_headers[1:] + filtered_file_headers[1:]
            csv_writer.writerow(combined_headers)
            aggregated_results.append(combined_headers)

            page_no = 0
            while True:
                page_no += 1
                base_url = f'https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/pulls?state=all&sort=created&direction=asc&page={page_no}'
                headers = {'Authorization': f'token {repo_info.repo_token}'} if repo_info.repo_token else {}
                headers['Accept'] = 'application/vnd.github.v3+json'
                response = requests.get(base_url, headers=headers)

                if response.status_code == 200:
                    prs = response.json()
                    if not prs:
                        break

                    for pr in prs:
                        try:
                            print(f"Extracting data for PR: {pr['number']}")
                            pr_age = self.calculate_age(pr['created_at'])
                            label_names = ",".join(label['name'] for label in pr['labels'])

                            commit_row = next((row for row in commit_rows if row[0] == pr['number']), None)
                            file_row = next((row for row in file_rows if row[0] == pr['number']), None)

                            commit_row = commit_row[1:] if commit_row else [''] * (len(commit_headers) - 1)
                            filtered_file_row = (
                                [file_row[i] for i in filtered_file_indices[1:]] if file_row
                                else [''] * (len(filtered_file_headers) - 1)
                            )

                            current_results = [
                                pr['number'], pr['state'], pr['created_at'], pr['updated_at'],
                                pr['closed_at'], pr['merged_at'], pr_age, len(pr['labels']),
                                label_names, pr['milestone']['open_issues'] if pr['milestone'] else 0,
                                pr['milestone']['closed_issues'] if pr['milestone'] else 0,
                                pr['head']['repo']['open_issues_count'], pr['head']['repo']['open_issues'],
                                pr['base']['repo']['open_issues_count'], pr['base']['repo']['open_issues'],
                                len(pr['assignees']), len(pr['requested_reviewers']), len(pr['requested_teams'])
                            ] + commit_row + filtered_file_row

                            aggregated_results.append(current_results)
                            csv_writer.writerow(current_results)

                        except Exception as e:
                            print(f"Error processing PR {pr['number']}: {e}")
                            continue

                else:
                    print(f"Failed to fetch Pull Requests on page: {page_no}. Status code: {response.status_code}. Repo: {repo_info.repo_name}")
                    print("Stopping Pull Request data extraction")
                    break

        print("Successfully extracted pull request data.")
        print(f"Final aggregated results: {aggregated_results}")

        if to_return:
            return aggregated_results




    def extract_branch_data(self, repo_info) -> list:
        '''
        Extracts branch data from the repository using PyGithub
        '''
        try:
            github_object = Github() if repo_info.repo_token is None else Github(auth=Auth.Token(repo_info.repo_token))
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

            return [param_names, extracted_data]

        except Exception as e:
            print(f"Failed to fetch branch data: {e}")
            return [[], []]
    
    def get_linked_issue_from_pr(self, repo_info) -> list:
        """
        Extracts linked issue data for all pull requests in the repository using the GitHub API.
        """
        # Add headers
        all_linked_issues = [[
            'PR Number',
            'Linked Issue Number',
            'Linked Issue Title'
        ]]

        page_no = 0
        while True:
            print(repo_info.repo_owner, repo_info.repo_name)
            page_no += 1
            base_url = f'https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/pulls?state=all&sort=created&direction=asc&page={page_no}'
            headers = {'Authorization': f'token {repo_info.repo_token}'} if repo_info.repo_token else {}
            headers['Accept'] = 'application/vnd.github.v3+json'

            response = requests.get(base_url, headers=headers)
            if response.status_code != 200:
                print(f"Failed to fetch PRs. Status code: {response.status_code}")
                break

            prs = response.json()
            if not prs:
                break

            for pr in prs:
                try:
                    pr_number = pr['number']
                    print(f"Processing linked issues for PR: {pr_number}")

                    timeline_page_no = 0
                    linked_issue = None
                    while True:
                        timeline_page_no += 1
                        timeline_url = f'https://api.github.com/repos/{repo_info.repo_owner}/{repo_info.repo_name}/issues/{pr_number}/timeline?page={timeline_page_no}'
                        timeline_headers = headers.copy()
                        timeline_headers['Accept'] = 'application/vnd.github.mockingbird-preview+json'

                        timeline_response = requests.get(timeline_url, headers=timeline_headers)
                        if timeline_response.status_code != 200:
                            break

                        events = timeline_response.json()
                        if not events:
                            break

                        for event in events:
                            if event.get('event') == 'cross-referenced':
                                source = event.get('source', {})
                                issue = source.get('issue')
                                if issue:
                                    linked_issue = issue
                                    break
                        if linked_issue:
                            break

                    if linked_issue:
                        all_linked_issues.append([
                            pr_number,
                            linked_issue['number'],
                            linked_issue.get('title', 'No Title')
                        ])
                    else:
                        all_linked_issues.append([
                            pr_number,
                            None,
                            None
                        ])

                except Exception as e:
                    print(f"Error processing linked issues for PR {pr_number}: {e}")

        return all_linked_issues

    
    def extract_data_commit_contributor(self):
        '''
        Extracts commit and contributor data from all the repository using the GitHub API and pydriller
        '''
        for repo_info in self.repo_infos:
            csv_filename = repo_info.repo_owner + '_' + repo_info.repo_name + '.csv'
            
            param_names = []
            extracted_data = []
            
            # Commit and contributor data
            commit_and_contributor_data = self.extract_commit_and_contributor_data(repo_info)


            # Combine all extracted data
            param_names = commit_and_contributor_data[0]
            extracted_data = commit_and_contributor_data[1]

            # Write to CSV
            self.write_to_csv_and_save([param_names, extracted_data], csv_filename, 'ExtractedData')

    def extract_general_overview(self):
        '''
        Extracts a general overview of the repository like file data, issue tracking data, linked issue with PRs, and branch data
        '''

        for repo_info in self.repo_infos:  # Loop through each repository
            csv_filename = f"{repo_info.repo_owner}_{repo_info.repo_name}.csv"

            try:

                # Extract repository-level data
                file_data_per_pr = self.extract_file_data_per_pr(repo_info)
                issue_tracking_data = self.extract_issue_tracking_data(repo_info)
                branch_data = self.extract_branch_data(repo_info)
                linked_data = self.get_linked_issue_from_pr(repo_info)

                # Combine parameter names
                param_names = (
                    file_data_per_pr[0] +
                    issue_tracking_data[0] +
                    branch_data[0] +
                    linked_data[0]
                )

                all_data = [] 

                # Extract PR-specific metrics
                pr_data = file_data_per_pr[1] + issue_tracking_data[1] + branch_data[1] + linked_data[1]

                # Replace None with empty strings for CSV compatibility
                pr_data = [value if value is not None else "" for value in pr_data]

                all_data.append(pr_data)
            except Exception as e:
                print(f"An error occurred while processing repo {repo_info.repo_name}: {e}")
                continue
            self.write_to_csv_and_save([param_names] + all_data, csv_filename, 'ExtractedData')

        print("General overview extraction completed.")

    def extract_data_pr(self):
        '''
        Extracts PR data from all repository using Github API and pydriller
        '''
        for repo_info in self.repo_infos:
            print(f"Extracting data for repo: {repo_info.repo_name}")
            csv_filename = repo_info.repo_owner + '_' + repo_info.repo_name + '.csv'
            print(f"PR data is stored in the following file: {csv_filename}")
            print("Extracting pull request data...")
            self.extract_pull_request_data(repo_info, csv_filename, False)
            print("")

            print("Extraction Complete.")
            print("")

    def extract_aggregate_metrics(self):
        """
        Extracts aggregate metrics from commit, file, and pull request data and saves them into a CSV file.
        """

        for repo_info in self.repo_infos:
                # Prepare CSV file name
            csv_filename = f"{repo_info.repo_owner}_{repo_info.repo_name}_PR.csv"
            try:
                # Extract commit data
                commit_data = self.extract_commit_data_per_pr(repo_info)
                if not commit_data[1]:
                    print(f"No commit data found for PR. Skipping.")

                # Extract file data
                file_data = self.extract_file_data_per_pr(repo_info)
                if not file_data[1]:
                    print(f"No file data found for PR. Skipping.")

                # Extract pull request data
                pr_data = self.extract_pull_request_data(repo_info, csv_filename, True)
                if not pr_data[0]:
                    print(f"No PR data found for PR. Skipping.")

                # Process PR quality metrics for all PRs
                pr_quality_data = self.calculate_pr_quality(repo_info)
                if not pr_quality_data[1]:
                    print(f"No PR Quality data found for PR. Skipping.")

                # Combine all metrics 
                # parameter_names = commit_data[0] + file_data[0][5:] + pr_data[0] + pr_quality_data[0]
                # extracted_data = commit_data[1:] + file_data[1][5:] + pr_data[1:] + pr_quality_data[1:]

            except Exception as e:
                print(f"An error occurred while processing repo {repo_info.repo_name}: {e}")
                continue

        print("Aggregate metrics extraction completed.")


def main():
    repo_name = ['translate_lib']
    repo_owners = ['aadityayadav']
    repo_tokens = [GITHUB_TOKEN]

    extraction = dataExtraction(repo_name, repo_owners, repo_tokens)

    # extraction.extract_general_overview()
    extraction.extract_aggregate_metrics()

    # extraction.extract_data_commit_contributor()

    # extraction.extract_data_pr()

    


if __name__ == "__main__":
    main()