# VEW product lifecycle

This diagram shows how VEW turns reusable software components into running
workbenches and virtual targets. A technology is a product grouping; it does
not restrict the product type. One technology can therefore contain both
`WORKBENCH` and `VIRTUAL_TARGET` products.

```mermaid
flowchart LR
    subgraph setup[Program and account setup]
        project[Project / program]
        technology[Technology<br/>product grouping]
        association[Onboarded project account<br/>stage + region]
        spoke[Spoke AWS account<br/>VPC and subnets]
        portfolio[Service Catalog portfolio]

        project -->|contains| technology
        project -->|registers| association
        technology -->|selected during onboarding| association
        association -->|identifies| spoke
        association -->|creates for the technology| portfolio
        portfolio -->|shared with| spoke
    end

    subgraph packaging[1. Package and build]
        component[Component]
        componentVersion[Component version]
        recipe[Recipe]
        recipeVersion[Recipe version]
        parentImage[Parent image]
        pipeline[Image pipeline]
        image[Built image / AMI]

        component -->|has| componentVersion
        componentVersion -->|assembled into| recipeVersion
        recipe -->|has| recipeVersion
        parentImage -->|base for| recipeVersion
        recipeVersion -->|built by| pipeline
        pipeline -->|produces| image
    end

    subgraph publishing[2. Publish]
        product[Product<br/>WORKBENCH or VIRTUAL_TARGET]
        productVersion[Product version distribution<br/>stage + region + spoke account]

        technology -->|groups| product
        pipeline -.->|may be linked for automatic publishing| product
        image -->|supplies the AMI| productVersion
        product -->|has| productVersion
        portfolio -->|contains published version| productVersion
    end

    subgraph provisioning[3. Provision and use]
        launch[User launches a product version]
        provisioned[Service Catalog provisioned product]
        workbench[Running workbench]
        target[Running virtual target]

        productVersion --> launch
        launch --> provisioned
        provisioned -->|when product type is WORKBENCH| workbench
        provisioned -->|when product type is VIRTUAL_TARGET| target
        spoke -->|hosts| workbench
        spoke -->|hosts| target
    end
```

The onboarding association establishes where versions for a technology are
published. Launching a product does not onboard the account again: every launch
creates another provisioned product in the spoke account selected by the
published version distribution.

## Relevant implementation

- Packaging entities: `backend/app/packaging/domain/model/`
- Technology and account association: `backend/app/projects/domain/model/`
- Portfolio, product, and version distribution: `backend/app/publishing/domain/model/`
- Runtime instance: `backend/app/provisioning/domain/model/provisioned_product.py`
