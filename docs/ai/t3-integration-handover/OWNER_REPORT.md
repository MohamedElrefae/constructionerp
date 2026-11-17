# Construction ERP and T3 — owner report

**As of 17 November 2026: integration under development; not production ready.**

The planned feature lets you follow a software task in the dashboard while the existing orchestration engine gives bounded work to T3, receives a proposed change in a separate task checkout, and runs checks before review. The model picker is intended to show model name, free/Go type and source. Engineering or commercial correctness still requires the checks and review appropriate to the work.

A disposable demonstration successfully sent a small builder task through the dashboard API and existing engine to T3, collected a change and passed an offline check. Separately, simulated authenticated-dashboard tests passed. These results do not establish that the live dashboard can execute production builder work. The actual production route remains disabled.

The Construction ERP repository already contains application work including BOQ, scope context, themes and form layouts. The integration work is a proposed enhancement to this existing application; this report does not certify those business areas as release ready.

To finish, the development team needs to choose and verify a working provider and service boundary, connect and test the authenticated live dashboard flow in a disposable project, and complete security, recovery and release checks. The accompanying developer report identifies what is proven and what is not. Do not enter real customer work into this integration until it has been verified and deployed.

The source is now consolidated into the existing Construction app. Retired debug folders and bench worktrees have been removed after verification, and the dashboard's scattered runtime folders have been replaced by one runtime directory. The dashboard is running and its accounts were preserved. This cleanup does not enable unfinished production builder dispatch.
