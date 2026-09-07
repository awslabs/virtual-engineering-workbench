# VEW domain relationships

This diagram focuses on the persisted domain entities and their cardinalities.
`ProductVersionDistribution` represents the publishing domain's `Version`
entity. A logical product version is stored once for each AWS account to which
it is distributed, using `(productId, versionId, awsAccountId)` as its key.

```mermaid
erDiagram
    PROJECT ||--o{ TECHNOLOGY : contains
    PROJECT ||--o{ PROJECT_ACCOUNT : registers
    TECHNOLOGY ||--o{ PROJECT_ACCOUNT : classifies
    TECHNOLOGY ||--o{ PORTFOLIO : owns
    PROJECT_ACCOUNT ||--o| PORTFOLIO : creates

    PROJECT ||--o{ COMPONENT_PROJECT_ASSOCIATION : grants_access_to
    COMPONENT ||--o{ COMPONENT_PROJECT_ASSOCIATION : is_shared_through
    COMPONENT ||--o{ COMPONENT_VERSION : versions
    RECIPE ||--o{ RECIPE_VERSION : versions
    COMPONENT_VERSION }o--o{ RECIPE_VERSION : is_included_in

    PROJECT ||--o{ RECIPE : owns
    PROJECT ||--o{ PIPELINE : owns
    PROJECT ||--o{ IMAGE : owns
    RECIPE_VERSION ||--o{ PIPELINE : configures
    PIPELINE ||--o{ IMAGE : builds

    PROJECT ||--o{ PRODUCT : owns
    TECHNOLOGY ||--o{ PRODUCT : groups
    PRODUCT o|--o{ PIPELINE : may_automate
    PRODUCT ||--o{ PRODUCT_VERSION_DISTRIBUTION : publishes
    IMAGE o|--o{ PRODUCT_VERSION_DISTRIBUTION : supplies_AMI_to
    PORTFOLIO ||--o{ PRODUCT_VERSION_DISTRIBUTION : contains
    PROJECT_ACCOUNT ||--o{ PRODUCT_VERSION_DISTRIBUTION : receives

    PROJECT ||--o{ PROVISIONED_PRODUCT : contains
    PRODUCT ||--o{ PROVISIONED_PRODUCT : launches_as
    PRODUCT_VERSION_DISTRIBUTION ||--o{ PROVISIONED_PRODUCT : is_source_for
    PROJECT_ACCOUNT ||--o{ PROVISIONED_PRODUCT : hosts

    PROJECT {
        string projectId PK
        string projectName
        boolean isActive
    }

    TECHNOLOGY {
        string id PK
        string projectId FK
        string name
    }

    PROJECT_ACCOUNT {
        string id PK
        string projectId FK
        string technologyId FK
        string awsAccountId
        string accountType
        string stage
        string region
        string accountStatus
    }

    PORTFOLIO {
        string technologyId PK
        string awsAccountId PK
        string portfolioId
        string projectId FK
        string accountId FK
        string stage
        string region
        string scPortfolioId
    }

    COMPONENT_PROJECT_ASSOCIATION {
        string componentId PK
        string projectId PK
    }

    COMPONENT {
        string componentId PK
        string componentName
        string componentPlatform
        string status
    }

    COMPONENT_VERSION {
        string componentId PK
        string componentVersionId PK
        string componentVersionName
        string softwareVersion
        string status
    }

    RECIPE {
        string projectId PK
        string recipeId PK
        string recipeName
        string recipePlatform
        string recipeArchitecture
        string recipeOsVersion
    }

    RECIPE_VERSION {
        string recipeId PK
        string recipeVersionId PK
        string parentImageUpstreamId
        list recipeComponentsVersions
        string status
    }

    PIPELINE {
        string projectId PK
        string pipelineId PK
        string recipeId FK
        string recipeVersionId FK
        string productId "optional product link"
        string pipelineSchedule
        string status
    }

    IMAGE {
        string projectId PK
        string imageId PK
        string pipelineId FK
        string recipeId FK
        string recipeVersionId FK
        string imageUpstreamId
        string status
    }

    PRODUCT {
        string projectId PK
        string productId PK
        string technologyId FK
        string productName
        string productType "WORKBENCH or VIRTUAL_TARGET"
        string status
    }

    PRODUCT_VERSION_DISTRIBUTION {
        string productId PK
        string versionId PK
        string awsAccountId PK
        string projectId FK
        string technologyId FK
        string accountId FK
        string stage
        string region
        string originalAmiId
        string scPortfolioId
        string scProductId
        string scProvisioningArtifactId
    }

    PROVISIONED_PRODUCT {
        string projectId PK
        string provisionedProductId PK
        string productId FK
        string versionId FK
        string technologyId FK
        string accountId FK
        string awsAccountId
        string provisionedProductType "WORKBENCH or VIRTUAL_TARGET"
        string stage
        string region
        string instanceId
        string status
    }
```

## Interpretation notes

- `Technology` groups products. It has no workbench or virtual-target type.
- `ProjectAccount` is the VEW association between a technology and a spoke AWS
  account for a stage and region.
- Onboarding a project account causes a Service Catalog `Portfolio` to be
  created for that technology and AWS account.
- A `Pipeline` always builds a particular recipe version. Its optional
  `productId` enables a completed image build to create a product version
  automatically.
- A publishing `Version` is a distribution record, not only a semantic version:
  it carries the target account, stage, region, portfolio, Service Catalog
  product, and provisioning artifact identifiers.
- `Product.productType` determines whether launches appear as workbenches or
  virtual targets. Both types follow the same publishing and provisioning
  relationships.

## Relevant implementation

- Projects: `backend/app/projects/domain/model/`
- Packaging: `backend/app/packaging/domain/model/`
- Publishing: `backend/app/publishing/domain/model/`
- Provisioning: `backend/app/provisioning/domain/model/provisioned_product.py`
