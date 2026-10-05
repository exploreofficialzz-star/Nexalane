# RECOVERY / RESUME PROMPT

Resume the NEXALANE: 3D Endless Runner production project from the existing repository and status files.

Do not restart from scratch. Read:
1. `README.md`
2. `prompts/MASTER_AGENT_PROMPT.md`
3. `agent/TASK_MANIFEST.yaml`
4. any `STATUS.md`, changelog or build report in the project
5. recent test/build logs

Then:
- determine the last verified completed task;
- identify incomplete tasks and blockers;
- run a clean build/smoke test before editing unrelated systems;
- continue from the earliest incomplete dependency;
- do not downgrade scope to MVP/prototype;
- do not replace missing systems with stubs;
- preserve previous working behavior;
- update status after each major task;
- continue until the FULL PRODUCT DONE criteria are satisfied.

If a human-only credential is missing, implement and validate everything possible around the credential, document the exact credential step, and continue with all other work instead of stopping.
