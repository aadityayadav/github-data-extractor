from github import Github, PullRequest, PaginatedList, TimelineEvent, Issue, Auth
import re

def get_linked_issue_from_pr(pr: PullRequest) -> Issue or None:
  """Check if the given pull request has a linked issue.

  This function iterates over the timeline of the pull request and checks if there is a 'cross-referenced' event.
  If such an event is found, it checks if the source of the event is a pull request and if so, it returns the pull request as an issue.

  Usage: 
  pr: PullRequest = repo.get_pull(number=8)
  issue_or_none = check_if_pr_has_linked_issue(pr)

  Args:
      pr (PullRequest): The pull request to check for a linked issue.

  Returns:
      Issue: The linked issue if it exists, None otherwise.
  """
  events_pages: PaginatedList[TimelineEvent] = pr.as_issue().get_timeline()
  pg_num = 0
  while events_pages.get_page(pg_num):
    page = events_pages.get_page(pg_num)
    pg_num += 1
    for e in page:
      if str(e.event) == 'cross-referenced':
        if e.source and e.source.issue:
            return e.source.issue


def calculate_pr_quality(pr_numbers: list) -> float:
        '''
        Calculates the PR quality based on the number of PRs with issues
        '''

        github_object = Github()
        prs_with_issues = 0
        repo =  github_object.get_repo(f"ishepard/pydriller")

        for pr_number in pr_numbers:
            pr: PullRequest = repo.get_pull(number=pr_number)
            issue_or_none = get_linked_issue_from_pr(pr)
            if issue_or_none is not None:
                print(issue_or_none)
                prs_with_issues += 1
        
        return prs_with_issues

pr_numbers = [7,5,4,3,2,1]

print("result:")
print(calculate_pr_quality(pr_numbers))