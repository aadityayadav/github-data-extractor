# # import requests


# # base_url = f'https://api.github.com/repos/ishepard/pydriller/issues?state=all&page=1'
# # import PyGithub
# # from github import Issue, PaginatedList, TimelineEvent, PullRequest

 
# # # If you have a GitHub token, you can use it for authentication, otherwise leave it as None
# # # headers = {'Authorization': f'token {repo_info.repo_token}'} if repo_info.repo_token is not None else {}
# # headers = {}
# # # Get all issues from the repository
# # response = requests.get(base_url, headers=headers)
# # print(response)
# # print("#####################")
# # rsp = response.json()
# # # print(rsp)
# # py = PyGithub.Github()
# # for rs in rsp:
# #     # if rs['updated_at'] > rs['created_at']:
# #     print(py.get_linked_pr_from_issue(rs))


# import subprocess
# import git
# import requests

# def run_code_duplication_detection(commit_hash, repository_path):
#     subprocess.run(["git", "checkout", commit_hash], cwd=repository_path)
#     # Run code duplication detection tool

# def analyze_commits_github_api(repo_owner, repo_name):
#     commits = get_commits(repo_owner, repo_name)

#     for commit in commits:
#         commit_hash = commit['sha']
#         clone_repo_and_analyze(commit_hash, repo_owner, repo_name)

# def clone_repo_and_analyze(commit_hash, repo_owner, repo_name):
#     # Clone the repository
#     subprocess.run(["git", "clone", f'https://github.com/{repo_owner}/{repo_name}.git'])

#     # Analyze code duplication
#     run_code_duplication_detection(commit_hash, repo_name)

# # Replace with your GitHub repository owner and name
# analyze_commits_github_api("owner", "repository")


import subprocess
import requests
import os

def get_commits(repo_owner, repo_name):
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/commits'
    response = requests.get(url)
    commits = response.json()
    return commits

def run_code_duplication_detection(commit_hash, repository_path):
    # Use 'git show' to get the content of a specific commit without switching branches
    command = ["git", "reset", "--hard", f"{commit_hash}"]
    result = subprocess.run(command, cwd=repository_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Process the content or save it for code duplication analysis
    content = result.stdout
    print(result)
    # Run code duplication detection tool on 'content'
    # Replace the command with the appropriate command for the code duplication detection tool
    command = ["clonedigger", repository_path]
    
    # Run the command
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    


def analyze_commits_github_api(repo_owner, repo_name):
    commits = get_commits(repo_owner, repo_name)
    if not os.path.exists(repo_name):
        subprocess.run(["git", "clone", f'https://github.com/{repo_owner}/{repo_name}.git'])
        

    for commit in commits:
        commit_hash = commit['sha']
        run_code_duplication_detection(commit_hash, repo_name)


# Replace with your GitHub repository owner and name
analyze_commits_github_api("ishepard", "pydriller")
