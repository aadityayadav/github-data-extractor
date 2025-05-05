'''
Git clone the required repository replace the repo name and path accordingly
'''
import os
import git
import re
from difflib import unified_diff
from collections import defaultdict

def extract_methods_from_content(content):
    method_pattern = re.compile(r'\b(?:public|private|protected|static|\s)*[\w<>,]+\s+(\w+) *\([^)]*\) *(\{?|[^;])')
    return set(method_pattern.findall(content))

def count_methods_in_file(file_path, diff_content):
    with open(f"REPO NAME HERE/{file_path}", 'r', encoding='utf-8') as file:
        original_content = file.read()

    added_methods = set()
    removed_methods = set()

    for line in unified_diff(original_content.splitlines(), diff_content.splitlines(), lineterm=''):
        if line.startswith('+') and 'class ' not in line:
            added_methods.update(extract_methods_from_content(line))
        elif line.startswith('-') and 'class ' not in line:
            removed_methods.update(extract_methods_from_content(line))

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

# Example usage
repository_path = 'REPO PATH HERE'
file_metrics, commit_metrics = analyze_repository(repository_path)

# Display results
print("File Metrics:")
for metric, value in file_metrics.items():
    print(f"{metric}: {value}")

print("\nCommit Metrics:")
for metric, value in commit_metrics.items():
    print(f"{metric}: {value}")
