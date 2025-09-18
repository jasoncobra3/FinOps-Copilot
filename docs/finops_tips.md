# FinOps Tips

1. Right-size compute: pick instance families with lower unit cost and scale vertically only when necessary.
2. Use reserved instances or savings plans for steady workloads.
3. Delete idle resources older than 30 days; reclaim snapshots and unattached volumes.
4. Ensure every resource has required tags:
   - owner: Team/individual responsible for costs (e.g., "team-a", "data-science")
   - project: Associated business project
   - env: Environment type (e.g., "prod", "dev", "staging")
   Missing tags create unknown/unattributed spend and prevent cost accountability.
5. Monitor sudden unit cost changes and verify billing currency/units.
6. Group small resources into aggregated budgets to avoid per-resource billing noise.

Note: Resources showing "unassigned" ownership need immediate tagging.
