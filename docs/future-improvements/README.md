# Future improvements

This directory records potential improvements to the Virtual Engineering Workbench (VEW). These documents capture research and design direction; they do not describe features that are currently available unless explicitly stated.

Each improvement document should include:

- the problem and desired outcome;
- verified current behavior;
- a proposed approach and alternatives;
- security and operational considerations;
- unresolved questions and a suggested delivery scope.

## Status terms

- **Research:** Current behavior has been investigated, but no design has been approved.
- **Proposed:** A preferred design has been identified but not implemented.
- **Planned:** An implementation plan has been approved.
- **Implemented:** The improvement is available and has been verified.

## Improvements

| Improvement | Status | Summary |
| --- | --- | --- |
| [Git as the source of truth](git-source-of-truth.md) | Research | Store component, recipe, and product definitions in Git while retaining VEW validation and lifecycle management. |
| [Terraform migration](terraform-migration.md) | Research | Replace the static CDK deployment with Terraform while preserving VEW's application-managed resource lifecycles. |
