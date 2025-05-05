# import os
# import git
# from collections import defaultdict


# def analyze_repository(repository_path):
#     repo = git.Repo(repository_path)

#     # File-based metrics
#     file_metrics = defaultdict(int)
#     # for commit in repo.iter_commits('--all'):
#     #     print(commit.diff())
#     #     for change in commit.diff():
#     #         file_metrics['new_files'] += int(change.new_file)
            
#     #         # Using line_stats for lines added and deleted
#     #         file_metrics['complexity_change'] += change.line_stats[1] - change.line_stats[2]
            
#     #         file_metrics['dependencies_change'] += len(change.diff('name-status').splitlines()) - 1

#     # Commit-based metrics
#     commit_metrics = defaultdict(int)
#     for commit in repo.iter_commits('--all'):
#         commit_metrics['modified_files_per_commit'] += len(commit.stats.files)
#         commit_metrics['modified_directories_per_commit'] += len(set(os.path.dirname(file) for file in commit.stats.files))
#         commit_metrics['lines_added_per_commit'] += commit.stats.total['insertions']
#         commit_metrics['lines_deleted_per_commit'] += commit.stats.total['deletions']
#         commit_metrics['methods_added_per_commit'] += commit.stats.total['lines']  # You may need to refine this based on your code structure
#         commit_metrics['methods_deleted_per_commit'] += commit.stats.total['lines']  # You may need to refine this based on your code structure
#         commit_metrics['bug_fix_commits'] += int('fix' in commit.message.lower())
#         print(commit_metrics)
#         print("#"*100)

#     return file_metrics, commit_metrics


# # Example usage
# repository_path = 'pydriller'
# file_metrics, commit_metrics = analyze_repository(repository_path)

# # Display results
# print("File Metrics:")
# for metric, value in file_metrics.items():
#     print(f"{metric}: {value}")

# print("\nCommit Metrics:")
# for metric, value in commit_metrics.items():
# #     print(f"{metric}: {value}")
# import os
# import git
# import re
# from collections import defaultdict

# def count_methods_in_file(file_path):
#     with open(file_path, 'r', encoding='utf-8') as file:
#         content = file.read()
#         method_pattern = re.compile(r'\b(?:public|private|protected|static|\s) +[\w<>,]+\s+(\w+) *\([^)]*\) *(\{?|[^;])')
#         methods = method_pattern.findall(content)
#         return len(methods)

# def analyze_repository(repository_path):
#     repo = git.Repo(repository_path)

#     # File-based metrics
#     file_metrics = defaultdict(int)
#     commit_metrics = defaultdict(int)
#     commit_count = 0
#     for commit in repo.iter_commits('--all'):
#         commit_metrics['modified_files_per_commit'] += len(commit.stats.files)
#         commit_metrics['modified_directories_per_commit'] += len(set(os.path.dirname(file) for file in commit.stats.files))
#         commit_metrics['lines_added_per_commit'] += commit.stats.total['insertions']
#         commit_metrics['lines_deleted_per_commit'] += commit.stats.total['deletions']
#         commit_metrics['bug_fix_commits'] += int('fix' in commit.message.lower())

#         for change in commit.diff():
#             commit_count += 1
#             file_metrics['new_files_rate'] += int(change.new_file)

#             # # Calculate lines added and deleted
#             # file_path = change.a_path
#             # try:
#             #     diff_cmd = f"git diff {commit.parents[0]} {commit} -- {file_path}"
#             #     diff_output = repo.git.execute(diff_cmd)
#             #     diff_lines = diff_output.splitlines()
#             #     lines_added = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
#             #     lines_deleted = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))

#             #     file_metrics['complexity_change'] += lines_added - lines_deleted

#             # except git.GitCommandError as e:
#             #     print(f"Error executing 'git diff' for {file_path}: {e}")


#             # Calculate methods added/deleted/modified
#             print(change.change_type, change.a_path, change.b_path)
#             if change.change_type in {'A', 'M'} and change.a_path.endswith('.java'):
#                 methods_added = count_methods_in_file(change.a_path)
#                 file_metrics['methods_added_per_commit'] += methods_added
#             if change.change_type in {'D', 'M'} and change.b_path.endswith('.java'):
#                 methods_deleted = count_methods_in_file(change.b_path)
#                 file_metrics['methods_deleted_per_commit'] += methods_deleted
    
#     file_metrics['new_files_rate'] = file_metrics['new_files_rate'] / commit_count
#     file_metrics['methods_added_per_commit'] = file_metrics['methods_added_per_commit'] / commit_count
#     file_metrics['methods_deleted_per_commit'] = file_metrics['methods_deleted_per_commit'] / commit_count

#     commit_metrics['modified_files_per_commit'] = commit_metrics['modified_files_per_commit'] / commit_count
#     commit_metrics['modified_directories_per_commit'] = commit_metrics['modified_directories_per_commit'] / commit_count
#     commit_metrics['lines_added_per_commit'] = commit_metrics['lines_added_per_commit'] / commit_count
#     commit_metrics['lines_deleted_per_commit'] = commit_metrics['lines_deleted_per_commit'] / commit_count
#     commit_metrics['bug_fix_commits'] = commit_metrics['bug_fix_commits'] / commit_count


#     # Commit-based metrics
    
#     # for commit in repo.iter_commits('--all'):
#     #     commit_metrics['modified_files_per_commit'] += len(commit.stats.files)
#     #     commit_metrics['modified_directories_per_commit'] += len(set(os.path.dirname(file) for file in commit.stats.files))
#     #     commit_metrics['lines_added_per_commit'] += commit.stats.total['insertions']
#     #     commit_metrics['lines_deleted_per_commit'] += commit.stats.total['deletions']
#     #     commit_metrics['bug_fix_commits'] += int('fix' in commit.message.lower())

#     return file_metrics, commit_metrics

# # Example usage
# repository_path = 'pydriller'
# file_metrics, commit_metrics = analyze_repository(repository_path)

# # Display results
# print("File Metrics:")
# for metric, value in file_metrics.items():
#     print(f"{metric}: {value}")

# print("\nCommit Metrics:")
# for metric, value in commit_metrics.items():
#     print(f"{metric}: {value}")import os
import git
import re
import os
from difflib import unified_diff
from collections import defaultdict

def count_methods_in_file(file_path, diff_content):
    with open(f"DSA-Bootcamp-Java/{file_path}", 'r', encoding='utf-8') as file:
        content = file.read()
        method_pattern = re.compile(r'\b(?:public|private|protected|static|\s)*[\w<>,]+\s+(\w+) *\([^)]*\) *(\{?|[^;])')
        methods = method_pattern.findall(content)

        original_methods = set(methods)
        modified_methods = set(method_pattern.findall(diff_content))

        added_methods = modified_methods - original_methods
        removed_methods = original_methods - modified_methods
        print(len(added_methods), len(removed_methods))

        return len(added_methods), len(removed_methods)

def analyze_repository(repository_path):
    repo = git.Repo(repository_path)

    # File-based metrics
    file_metrics = defaultdict(int)
    commit_metrics = defaultdict(int)
    commit_count = 0

    for commit in repo.iter_commits('--all'):
        commit_metrics['modified_files_per_commit'] += len(commit.stats.files)
        commit_metrics['modified_directories_per_commit'] += len(set(os.path.dirname(file) for file in commit.stats.files))
        commit_metrics['lines_added_per_commit'] += commit.stats.total['insertions']
        commit_metrics['lines_deleted_per_commit'] += commit.stats.total['deletions']
        commit_metrics['bug_fix_commits'] += int('fix' in commit.message.lower())

        methods_added_per_commit = 0
        methods_deleted_per_commit = 0

        for change in commit.diff():
            commit_count += 1
            file_metrics['new_files_rate'] += int(change.new_file)

            # Calculate methods added/deleted/modified
            print(change.change_type, change.a_path, change.b_path)
            if change.change_type in {'A', 'M'} and change.a_path.endswith('.java'):
                methods_added, _ = count_methods_in_file(change.a_path, change.diff)
                methods_added_per_commit += methods_added
            if change.change_type in {'D', 'M'} and change.b_path.endswith('.java'):
                _, methods_deleted = count_methods_in_file(change.b_path, change.diff)
                methods_deleted_per_commit += methods_deleted

        file_metrics['methods_added_per_commit'] += methods_added_per_commit
        file_metrics['methods_deleted_per_commit'] += methods_deleted_per_commit
    
    file_metrics['new_files_rate'] = file_metrics['new_files_rate'] / commit_count
    file_metrics['methods_added_per_commit'] = file_metrics['methods_added_per_commit'] / commit_count
    file_metrics['methods_deleted_per_commit'] = file_metrics['methods_deleted_per_commit'] / commit_count

    commit_metrics['modified_files_per_commit'] = commit_metrics['modified_files_per_commit'] / commit_count
    commit_metrics['modified_directories_per_commit'] = commit_metrics['modified_directories_per_commit'] / commit_count
    commit_metrics['lines_added_per_commit'] = commit_metrics['lines_added_per_commit'] / commit_count
    commit_metrics['lines_deleted_per_commit'] = commit_metrics['lines_deleted_per_commit'] / commit_count
    commit_metrics['bug_fix_commits'] = commit_metrics['bug_fix_commits'] / commit_count

    return file_metrics, commit_metrics


repository_path = 'DSA-Bootcamp-Java'
file_metrics, commit_metrics = analyze_repository(repository_path)

print("File Metrics:")
for metric, value in file_metrics.items():
    print(f"{metric}: {value}")

print("\nCommit Metrics:")
for metric, value in commit_metrics.items():
    print(f"{metric}: {value}")
