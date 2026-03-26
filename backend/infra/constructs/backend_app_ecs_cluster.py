import constructs
from aws_cdk import aws_ec2, aws_ecs


class BackendAppEcsCluster(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        cluster_name: str,
        vpc: aws_ec2.IVpc,
    ) -> None:
        super().__init__(scope, id)

        self.__ecs_cluster = aws_ecs.Cluster(
            self,
            "BackendAppEcsCluster",
            cluster_name=cluster_name,
            container_insights=True,
            enable_fargate_capacity_providers=True,
            vpc=vpc,
        )

    @property
    def ecs_cluster(self) -> aws_ecs.Cluster:
        return self.__ecs_cluster
