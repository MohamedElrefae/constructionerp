# Construction access setup

Audience: the authorized implementation engineer or operator. These are explicit configuration steps, not automatic production activation. A fresh installation creates app roles and screens; rehearsal-site Custom DocPerm grants are not a substitute for configuring the customer site.

## Preserve native permissions

Use ERPNext's Role Permission Manager to add approved rules. Its native permission API initializes custom permissions by copying the standard table. Never insert a first Custom DocPerm row directly: any custom rows replace the effective standard table. Compare the complete before/after table and retain all unrelated role rights. Review copied rows again after vendor upgrades.

Native transaction roles remain responsible for purchasing, stock and accounting. Construction permissions, Company User Permissions, active scope and server business guards also apply; a role name or visible workspace grants no action by itself.

## Explicit role configuration

Before granting Company read, configure the intended accounts' Company User Permissions and active scope. Check that each can access its allowed company and is refused another. Preserve dedicated missing-scope denial accounts. Do not grant System Manager to bypass a failed workflow.

| Role | DocType | Intended grant |
| --- | --- | --- |
| Project Manager, Construction Owner, Site Engineer, Read-Only | Company | Read only |
| Cost Database Maintainer | Company | Read only |
| Cost Database Maintainer | Item | Read, create; no write/delete |
| Cost Database Maintainer | UOM | Read, create; no write/delete |
| Cost Database Maintainer | Resource Price History | Read, create; no write/delete |
| Cost Database Maintainer | BOQ Cost Analysis | Read, create, write; no submit/cancel/delete |
| Cost Database Maintainer | BOQ Header, BOQ Item | Read only |

Grant only the documented workflow actions. Leave analysis auto-submit disabled. Compatible shared Items must be reused unchanged; conflicting rows must be refused. Role configuration does not authorize modification of live ERPNext Items. Cost/resource views additionally check their source rows; Company read alone grants no price history or accounting ledger access.

Where native transaction validation requires the separately reviewed additions, Stock User has Account read and Accounts Manager has Item read, while all unrelated native rights remain intact.

## Qualification before use

Using ordinary accounts, verify allowed/denied company and project reads, missing scope, import preview/commit, repricing, submit/cancel refusals and native transaction handoffs. Check persisted state after denied mutations. Record the site, app/framework candidate and effective permission table. Production role activation requires the owner's separate decision.
