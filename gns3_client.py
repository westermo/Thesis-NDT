import requests, random

class GNS3Client:
    def __init__(self, host="localhost", port="3080"):
        self.base_url = f"http://{host}:{port}/v2"

    def get_projects(self):
        pass

    def create_project(self, project_name):
        pass

    def get_project(self, project_id):
        pass
