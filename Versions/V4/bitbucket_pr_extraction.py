from itertools import zip_longest
from datetime import datetime
import requests
import csv
import os



class repoInfo:
    def __init__(self, repo_owner: str, repo_name: str, username: str = None, password: str = None):
        self.username = username
        self.password = password
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.bitbucket.org/2.0/repositories/{repo_owner}/{repo_name}/pullrequests"


class dataExtraction:
    def __init__(self, repo_owner: str, repo_name: str, username: str = None, password: str = None):
        '''
        Initializes the repo_info list with the repo names, owners and auth
        '''
        self.repo_info = repoInfo(repo_owner, repo_name, username, password) 



    def extract_pull_request_data(self, csv_filename: str):
        '''
        Extracts pull request data from the repository using the GitHub API
        '''

        # Note: we are writing in the csv file directly instead of returning the data to save system memory
        # Check if the folder exists, create it if not
        if not os.path.exists('ExtractedData'):
            os.makedirs('ExtractedData')

        file_path = os.path.join('ExtractedData', csv_filename)

        # get pr data
        url = self.repo_info.base_url

        response = requests.get(url, auth=(self.repo_info.username, self.repo_info.password)) if self.repo_info.username and self.repo_info.password else requests.get(url)
        if response.status_code == 200:
            pr_data = response.json().get('values', [])
        else:
            print(f"Failed to fetch pull requests. Status code: {response.status_code}")
            

        with open(file_path, 'w', newline='') as csv_file:
            fieldnames = ['ID', 'Title', 'State', 'Created At', 'Updated At', 'Author', 'Reviewers']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

            for pr in pr_data:
                reviewers = ", ".join([reviewer['display_name'] for reviewer in pr.get('reviewers', [])])
                writer.writerow({
                    'ID': pr['id'],
                    'Title': pr['title'],
                    'State': pr['state'],
                    'Created At': pr['created_on'],
                    'Updated At': pr['updated_on'],
                    'Author': pr['author']['display_name'],
                    'Reviewers': reviewers
                })

        print("Successfully extracted pull request data.")
    
        
    def extract_data(self):
        '''
        Extracts data from the repository
        '''

        csv_filename = self.repo_info.repo_owner + '_' + self.repo_info.repo_name + '.csv'
        self.extract_pull_request_data(csv_filename)

        print(f"PR data is stored in the following file: {csv_filename}")
        
            

def main():
    username = ""
    password = ""
    repository_owner = "Mediacurrent"
    repository_name = "rain_theme"

    extractor = dataExtraction(repository_owner, repository_name, username, password)

    extractor.extract_data()

if __name__ == "__main__":
    main()