# Synthetic Terraform change review runbook

## Destructive and replacement changes
Review deletions and both replacement orders. Stateful resources need a recent restorable backup, dependency assessment and recovery owner. Creating before destroying does not remove state or cutover risk. Confirm whether resource names, quotas or provider behavior can prevent parallel instances. A planned removal from Terraform management changes ownership but does not itself delete the object.

## Public ingress and protection
New 0.0.0.0/0 or ::/0 ingress requires a port, authentication and exposure review. Public egress is not equivalent to inbound exposure. A change disabling deletion protection for a stateful system needs specific scrutiny. Evaluate blast radius and exception ownership.

## Unknown values and incomplete plans
Values computed at apply time limit pre-apply assessment. An errored or incomplete plan cannot be assumed safe. Review the final plan immediately before execution and verify configuration and provider versions. This tool uses curated resource metadata, never raw secrets or variable values, for model context.

## Rollout and rollback
Document rollback feasibility, a recovery owner, observable stop conditions and a change window. Use staged changes where dependencies allow. Restoring a state backup is not a universal rollback method. Human reviewers must validate any model-generated recommendation against the actual platform.

Examples are synthetic. Risk levels are review heuristics, not probabilities or approval decisions.
