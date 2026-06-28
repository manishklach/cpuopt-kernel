# ARM Notes

ARM CPU tuning is highly platform-specific because firmware frequently owns policy decisions.

## Areas of interest

- SCMI performance protocol
- PSCI coordination
- `cpufreq-dt`
- heterogeneous topologies such as big.LITTLE
- thermal framework ownership

## Why ARM differs

ARM systems often route performance policy through firmware or SCMI rather than vendor CPU
registers directly exposed to the OS. Safe tuning therefore requires platform-aware handling
and strong discovery before any policy write path.
