"""
Architecture diagram for the ECS CI/CD lab.

Requirements:
    pip install diagrams
    sudo apt install graphviz -y

Run:
    python architecture.py
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import ECS, Fargate
from diagrams.aws.network import VPC, ALB, NATGateway, InternetGateway
from diagrams.aws.devtools import Codepipeline, Codedeploy
from diagrams.aws.integration import Eventbridge
from diagrams.aws.storage import S3
from diagrams.aws.security import IAMRole
from diagrams.aws.management import Cloudwatch
from diagrams.aws.network import Endpoint as VPCEndpoint
from diagrams.onprem.vcs import Github
from diagrams.aws.compute import ECR

graph_attr = {
    "fontsize": "13",
    "bgcolor": "white",
    "pad": "0.5",
    "splines": "ortho",
}

with Diagram(
    "ECS CI/CD Architecture — Abdul Basit Mohammed",
    filename="architecture",
    outformat="png",
    show=False,
    graph_attr=graph_attr,
    direction="LR",
):
    github = Github("GitHub\necs-app repo")
    ecr = ECR("Amazon ECR\necs-lab-app")
    eventbridge = Eventbridge("EventBridge\nECR Push Rule")
    pipeline = Codepipeline("CodePipeline")
    codedeploy = Codedeploy("CodeDeploy\nBlue/Green")
    artifacts = S3("S3\nArtifact Bucket")
    logs = Cloudwatch("CloudWatch\nLogs")
    oidc = IAMRole("OIDC Role\n(GitHub Actions)")

    with Cluster("AWS Region: eu-central-1 (Frankfurt)"):
        with Cluster("Custom VPC  10.0.0.0/16"):

            with Cluster("Public Subnets\n(eu-central-1a / eu-central-1b)"):
                igw = InternetGateway("Internet\nGateway")
                alb = ALB("Application\nLoad Balancer\n:80 (prod)\n:8080 (test)")
                nat1 = NATGateway("NAT GW\nAZ-1a")
                nat2 = NATGateway("NAT GW\nAZ-1b")

            with Cluster("Private Subnets\n(eu-central-1a / eu-central-1b)"):
                with Cluster("ECS Fargate Service\n(Blue / Green tasks)"):
                    task_blue = Fargate("Task\n(Blue)")
                    task_green = Fargate("Task\n(Green)")

                with Cluster("VPC Endpoints"):
                    ep_ecr_api = VPCEndpoint("ECR API")
                    ep_ecr_dkr = VPCEndpoint("ECR DKR")
                    ep_s3 = VPCEndpoint("S3 Gateway")
                    ep_logs = VPCEndpoint("CloudWatch\nLogs")

    # CI flow
    github >> Edge(label="OIDC AssumeRole") >> oidc
    github >> Edge(label="docker push\n(sha-<commit>)") >> ecr

    # CD trigger
    ecr >> Edge(label="image push event") >> eventbridge
    eventbridge >> Edge(label="StartPipelineExecution") >> pipeline
    artifacts >> Edge(label="appspec.json\ntaskdef.json") >> pipeline
    pipeline >> codedeploy
    codedeploy >> Edge(label="deploy green") >> task_green
    codedeploy >> Edge(label="shift traffic") >> alb

    # Traffic flow
    igw >> alb
    alb >> Edge(label=":80") >> task_blue
    alb >> Edge(label=":8080 test") >> task_green

    # Private connectivity
    task_blue >> ep_ecr_api
    task_blue >> ep_ecr_dkr
    task_blue >> ep_s3
    task_blue >> ep_logs >> logs
    task_blue >> nat1

    task_green >> ep_ecr_api
    task_green >> ep_ecr_dkr
    task_green >> ep_s3
    task_green >> ep_logs
    task_green >> nat2

    ep_ecr_api >> ecr
    ep_ecr_dkr >> ecr
