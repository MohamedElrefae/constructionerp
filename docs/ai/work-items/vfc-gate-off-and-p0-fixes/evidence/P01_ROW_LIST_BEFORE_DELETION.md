# P0-1 Row List — PUBLISHED BEFORE DELETION (D3 condition 2)

- **Generated (UTC):** 2026-11-11T22:38:23Z
- **Site:** `v16.localhost`  ·  **DB:** `_6d52b48c328b294e`
- **Predicate:** `profile_name LIKE '\_Test\_%'`
- **Rows to delete:** 202 of 210 total
- **Rows preserved:** 8 (the real default profiles)

## Summary by target doctype

| reference_doctype | rows to delete | enabled=1 | is_default=1 | real profile exists? |
|---|---:|---:|---:|---|
| Task | 200 | 200 | 0 | **NO — 0 real Task profiles** |
| User Scope Context | 2 | 2 | 0 | yes (User Scope Context-Default) |
| **Total** | **202** | **202** | **0** | |

## Pre-deletion risk analysis

| Check | Result |
|---|---|
| `for_user` set (resolver Step 1 matchable) | **0 / 202** |
| `for_role` set (resolver Step 2 matchable) | **0 / 202** |
| `is_default=1` (resolver Step 3 matchable) | **0 / 202** |
| `is_system=1` (blocks API deletion) | **202 / 202** |
| `enabled=1` (appear in profile lists) | **202 / 202** |
| non-empty `sections_json` | **202 / 202** |
| priority | all = 10 |

> **Resolver impact: NONE.** All three resolution steps match zero of these rows,
> so no user's layout resolves to them today. Deleting them cannot change any
> resolved layout.
>
> **List impact: REAL.** They are `enabled=1`, so they are returned by
> `frappe.get_all(filters={reference_doctype, enabled:1})` and pollute the
> Task profile list (200 of 200 rows).
>
> **Why they were never cleaned up:** all 202 carry `is_system=1`, and both
> `delete_my_personal_layout` and `delete_layout` throw
> *"System-seeded profiles cannot be deleted. Disable them instead."*
> The normal API path is structurally incapable of removing them.

## Post-deletion behaviour (predicted, no change expected)

- **Task** — 0 real profiles today → resolver returns `None` → native layout.
  After deletion: still 0 profiles → `None` → native layout. **Unchanged.**
- **User Scope Context** — Step 3 already selects `User Scope Context-Default`
  (`is_default=1`) over the 2 test rows (`is_default=0`). **Unchanged.**

## The 202 rows

```
name	profile_name	reference_doctype	enabled	is_default	priority	layout_version
Task-_Test_01a1a7	_Test_01a1a7	Task	1	0	10	1
Task-_Test_025b09	_Test_025b09	Task	1	0	10	1
Task-_Test_04b353	_Test_04b353	Task	1	0	10	1
Task-_Test_0948c6	_Test_0948c6	Task	1	0	10	1
Task-_Test_0bec3f	_Test_0bec3f	Task	1	0	10	1
Task-_Test_0d53a0	_Test_0d53a0	Task	1	0	10	1
Task-_Test_0eba05	_Test_0eba05	Task	1	0	10	1
Task-_Test_118498	_Test_118498	Task	1	0	10	1
Task-_Test_123221	_Test_123221	Task	1	0	10	1
Task-_Test_13fffc	_Test_13fffc	Task	1	0	10	1
Task-_Test_14af1e	_Test_14af1e	Task	1	0	10	1
Task-_Test_15075b	_Test_15075b	Task	1	0	10	1
Task-_Test_158cd3	_Test_158cd3	Task	1	0	10	1
Task-_Test_15a750	_Test_15a750	Task	1	0	10	1
Task-_Test_16ea76	_Test_16ea76	Task	1	0	10	1
Task-_Test_17cb61	_Test_17cb61	Task	1	0	10	1
Task-_Test_1832ee	_Test_1832ee	Task	1	0	10	1
Task-_Test_185298	_Test_185298	Task	1	0	10	1
Task-_Test_1943ce	_Test_1943ce	Task	1	0	10	1
Task-_Test_1a827d	_Test_1a827d	Task	1	0	10	1
Task-_Test_1ac336	_Test_1ac336	Task	1	0	10	1
Task-_Test_1c9e09	_Test_1c9e09	Task	1	0	10	1
Task-_Test_1cda5f	_Test_1cda5f	Task	1	0	10	1
Task-_Test_1dd2e2	_Test_1dd2e2	Task	1	0	10	1
Task-_Test_236118	_Test_236118	Task	1	0	10	1
Task-_Test_24e87f	_Test_24e87f	Task	1	0	10	1
Task-_Test_2636b8	_Test_2636b8	Task	1	0	10	1
Task-_Test_272dd0	_Test_272dd0	Task	1	0	10	1
Task-_Test_2761f4	_Test_2761f4	Task	1	0	10	1
Task-_Test_277a38	_Test_277a38	Task	1	0	10	1
Task-_Test_27d0e0	_Test_27d0e0	Task	1	0	10	1
Task-_Test_282351	_Test_282351	Task	1	0	10	1
Task-_Test_2b386e	_Test_2b386e	Task	1	0	10	1
Task-_Test_2b3be3	_Test_2b3be3	Task	1	0	10	1
Task-_Test_2b7f13	_Test_2b7f13	Task	1	0	10	1
Task-_Test_2c1659	_Test_2c1659	Task	1	0	10	1
Task-_Test_2d0757	_Test_2d0757	Task	1	0	10	1
Task-_Test_2dda6c	_Test_2dda6c	Task	1	0	10	1
Task-_Test_2f4732	_Test_2f4732	Task	1	0	10	1
Task-_Test_2f7ef4	_Test_2f7ef4	Task	1	0	10	1
Task-_Test_312790	_Test_312790	Task	1	0	10	1
Task-_Test_319246	_Test_319246	Task	1	0	10	1
Task-_Test_3379be	_Test_3379be	Task	1	0	10	1
Task-_Test_345a02	_Test_345a02	Task	1	0	10	1
Task-_Test_355d6e	_Test_355d6e	Task	1	0	10	1
Task-_Test_38e8a8	_Test_38e8a8	Task	1	0	10	1
Task-_Test_3b0b1b	_Test_3b0b1b	Task	1	0	10	1
Task-_Test_3bb2c6	_Test_3bb2c6	Task	1	0	10	1
Task-_Test_3bed13	_Test_3bed13	Task	1	0	10	1
Task-_Test_3f9746	_Test_3f9746	Task	1	0	10	1
Task-_Test_42152b	_Test_42152b	Task	1	0	10	1
Task-_Test_439997	_Test_439997	Task	1	0	10	1
Task-_Test_43db82	_Test_43db82	Task	1	0	10	1
Task-_Test_455004	_Test_455004	Task	1	0	10	1
Task-_Test_48a61f	_Test_48a61f	Task	1	0	10	1
Task-_Test_49bf8c	_Test_49bf8c	Task	1	0	10	1
Task-_Test_4a10ed	_Test_4a10ed	Task	1	0	10	1
Task-_Test_4b3a93	_Test_4b3a93	Task	1	0	10	1
Task-_Test_4f5284	_Test_4f5284	Task	1	0	10	1
Task-_Test_50da4c	_Test_50da4c	Task	1	0	10	1
Task-_Test_517dc5	_Test_517dc5	Task	1	0	10	1
Task-_Test_52930e	_Test_52930e	Task	1	0	10	1
Task-_Test_53339a	_Test_53339a	Task	1	0	10	1
Task-_Test_5349d1	_Test_5349d1	Task	1	0	10	1
Task-_Test_555541	_Test_555541	Task	1	0	10	1
Task-_Test_559024	_Test_559024	Task	1	0	10	1
Task-_Test_5706df	_Test_5706df	Task	1	0	10	1
Task-_Test_570983	_Test_570983	Task	1	0	10	1
Task-_Test_5721c6	_Test_5721c6	Task	1	0	10	1
Task-_Test_57bbde	_Test_57bbde	Task	1	0	10	1
Task-_Test_585639	_Test_585639	Task	1	0	10	1
Task-_Test_5986b1	_Test_5986b1	Task	1	0	10	1
Task-_Test_59934b	_Test_59934b	Task	1	0	10	1
Task-_Test_5a2c02	_Test_5a2c02	Task	1	0	10	1
Task-_Test_5d0ca2	_Test_5d0ca2	Task	1	0	10	1
Task-_Test_5de346	_Test_5de346	Task	1	0	10	1
Task-_Test_5f6c0e	_Test_5f6c0e	Task	1	0	10	1
Task-_Test_5ff2e7	_Test_5ff2e7	Task	1	0	10	1
Task-_Test_611416	_Test_611416	Task	1	0	10	1
Task-_Test_62401b	_Test_62401b	Task	1	0	10	1
Task-_Test_65bba2	_Test_65bba2	Task	1	0	10	1
Task-_Test_65c0a7	_Test_65c0a7	Task	1	0	10	1
Task-_Test_675540	_Test_675540	Task	1	0	10	1
Task-_Test_6815a8	_Test_6815a8	Task	1	0	10	1
Task-_Test_691391	_Test_691391	Task	1	0	10	1
Task-_Test_6a2e43	_Test_6a2e43	Task	1	0	10	1
Task-_Test_6cf775	_Test_6cf775	Task	1	0	10	1
Task-_Test_6ecde5	_Test_6ecde5	Task	1	0	10	1
Task-_Test_701922	_Test_701922	Task	1	0	10	1
Task-_Test_70b83b	_Test_70b83b	Task	1	0	10	1
Task-_Test_72f759	_Test_72f759	Task	1	0	10	1
Task-_Test_763e57	_Test_763e57	Task	1	0	10	1
Task-_Test_768984	_Test_768984	Task	1	0	10	1
Task-_Test_787f4a	_Test_787f4a	Task	1	0	10	1
Task-_Test_788a51	_Test_788a51	Task	1	0	10	1
Task-_Test_7a7426	_Test_7a7426	Task	1	0	10	1
Task-_Test_7b04ca	_Test_7b04ca	Task	1	0	10	1
Task-_Test_7cedd1	_Test_7cedd1	Task	1	0	10	1
Task-_Test_7dacdb	_Test_7dacdb	Task	1	0	10	1
Task-_Test_7ed832	_Test_7ed832	Task	1	0	10	1
Task-_Test_7ee0d1	_Test_7ee0d1	Task	1	0	10	1
Task-_Test_7eeb72	_Test_7eeb72	Task	1	0	10	1
Task-_Test_7fa6f2	_Test_7fa6f2	Task	1	0	10	1
Task-_Test_8005be	_Test_8005be	Task	1	0	10	1
Task-_Test_81f420	_Test_81f420	Task	1	0	10	1
Task-_Test_825b84	_Test_825b84	Task	1	0	10	1
Task-_Test_82be36	_Test_82be36	Task	1	0	10	1
Task-_Test_82e479	_Test_82e479	Task	1	0	10	1
Task-_Test_8399e1	_Test_8399e1	Task	1	0	10	1
Task-_Test_841c80	_Test_841c80	Task	1	0	10	1
Task-_Test_84af76	_Test_84af76	Task	1	0	10	1
Task-_Test_856cec	_Test_856cec	Task	1	0	10	1
Task-_Test_8b1979	_Test_8b1979	Task	1	0	10	1
Task-_Test_8c13ec	_Test_8c13ec	Task	1	0	10	1
Task-_Test_904e8f	_Test_904e8f	Task	1	0	10	1
Task-_Test_919855	_Test_919855	Task	1	0	10	1
Task-_Test_92157a	_Test_92157a	Task	1	0	10	1
Task-_Test_925afa	_Test_925afa	Task	1	0	10	1
Task-_Test_93bcdb	_Test_93bcdb	Task	1	0	10	1
Task-_Test_93f8bf	_Test_93f8bf	Task	1	0	10	1
Task-_Test_94724e	_Test_94724e	Task	1	0	10	1
Task-_Test_94d2f7	_Test_94d2f7	Task	1	0	10	1
Task-_Test_951890	_Test_951890	Task	1	0	10	1
Task-_Test_9522eb	_Test_9522eb	Task	1	0	10	1
Task-_Test_95e380	_Test_95e380	Task	1	0	10	1
Task-_Test_9873e1	_Test_9873e1	Task	1	0	10	1
Task-_Test_9a5062	_Test_9a5062	Task	1	0	10	1
Task-_Test_9ad206	_Test_9ad206	Task	1	0	10	1
Task-_Test_9bbf68	_Test_9bbf68	Task	1	0	10	1
Task-_Test_9c82bf	_Test_9c82bf	Task	1	0	10	1
Task-_Test_9fc985	_Test_9fc985	Task	1	0	10	1
Task-_Test_a0d30c	_Test_a0d30c	Task	1	0	10	1
Task-_Test_a34807	_Test_a34807	Task	1	0	10	1
Task-_Test_a5098b	_Test_a5098b	Task	1	0	10	1
Task-_Test_ab398c	_Test_ab398c	Task	1	0	10	1
Task-_Test_ad2e1b	_Test_ad2e1b	Task	1	0	10	1
Task-_Test_ad954c	_Test_ad954c	Task	1	0	10	1
Task-_Test_b0c4da	_Test_b0c4da	Task	1	0	10	1
Task-_Test_b156fe	_Test_b156fe	Task	1	0	10	1
Task-_Test_b55b06	_Test_b55b06	Task	1	0	10	1
Task-_Test_b57df4	_Test_b57df4	Task	1	0	10	1
Task-_Test_b7e2bc	_Test_b7e2bc	Task	1	0	10	1
Task-_Test_ba22dc	_Test_ba22dc	Task	1	0	10	1
Task-_Test_ba406c	_Test_ba406c	Task	1	0	10	1
Task-_Test_bb1a0a	_Test_bb1a0a	Task	1	0	10	1
Task-_Test_bcaf06	_Test_bcaf06	Task	1	0	10	1
Task-_Test_bcfd72	_Test_bcfd72	Task	1	0	10	1
Task-_Test_bf638a	_Test_bf638a	Task	1	0	10	1
Task-_Test_bfcb5d	_Test_bfcb5d	Task	1	0	10	1
Task-_Test_c1fe40	_Test_c1fe40	Task	1	0	10	1
Task-_Test_c3382d	_Test_c3382d	Task	1	0	10	1
Task-_Test_c57815	_Test_c57815	Task	1	0	10	1
Task-_Test_c84c6c	_Test_c84c6c	Task	1	0	10	1
Task-_Test_c89dca	_Test_c89dca	Task	1	0	10	1
Task-_Test_c94006	_Test_c94006	Task	1	0	10	1
Task-_Test_cc3265	_Test_cc3265	Task	1	0	10	1
Task-_Test_cca051	_Test_cca051	Task	1	0	10	1
Task-_Test_cd6914	_Test_cd6914	Task	1	0	10	1
Task-_Test_ce3f53	_Test_ce3f53	Task	1	0	10	1
Task-_Test_ce5417	_Test_ce5417	Task	1	0	10	1
Task-_Test_ce70c3	_Test_ce70c3	Task	1	0	10	1
Task-_Test_cea4ac	_Test_cea4ac	Task	1	0	10	1
Task-_Test_d0293c	_Test_d0293c	Task	1	0	10	1
Task-_Test_d08ef8	_Test_d08ef8	Task	1	0	10	1
Task-_Test_d2bd57	_Test_d2bd57	Task	1	0	10	1
Task-_Test_d3e0c7	_Test_d3e0c7	Task	1	0	10	1
Task-_Test_d496d9	_Test_d496d9	Task	1	0	10	1
Task-_Test_d7c419	_Test_d7c419	Task	1	0	10	1
Task-_Test_dac118	_Test_dac118	Task	1	0	10	1
Task-_Test_dae1dc	_Test_dae1dc	Task	1	0	10	1
Task-_Test_db0d93	_Test_db0d93	Task	1	0	10	1
Task-_Test_db2d71	_Test_db2d71	Task	1	0	10	1
Task-_Test_dc778e	_Test_dc778e	Task	1	0	10	1
Task-_Test_df944f	_Test_df944f	Task	1	0	10	1
Task-_Test_e007a0	_Test_e007a0	Task	1	0	10	1
Task-_Test_e0b0cd	_Test_e0b0cd	Task	1	0	10	1
Task-_Test_e0f305	_Test_e0f305	Task	1	0	10	1
Task-_Test_e16752	_Test_e16752	Task	1	0	10	1
Task-_Test_e3a82f	_Test_e3a82f	Task	1	0	10	1
Task-_Test_e3c70e	_Test_e3c70e	Task	1	0	10	1
Task-_Test_ea2af5	_Test_ea2af5	Task	1	0	10	1
Task-_Test_ea8cb3	_Test_ea8cb3	Task	1	0	10	1
Task-_Test_eb70c2	_Test_eb70c2	Task	1	0	10	1
Task-_Test_ebdc3e	_Test_ebdc3e	Task	1	0	10	1
Task-_Test_eef542	_Test_eef542	Task	1	0	10	1
Task-_Test_ef0398	_Test_ef0398	Task	1	0	10	1
Task-_Test_f0c8f4	_Test_f0c8f4	Task	1	0	10	1
Task-_Test_f16df4	_Test_f16df4	Task	1	0	10	1
Task-_Test_f1ee8d	_Test_f1ee8d	Task	1	0	10	1
Task-_Test_f32805	_Test_f32805	Task	1	0	10	1
Task-_Test_f38b4a	_Test_f38b4a	Task	1	0	10	1
Task-_Test_f417f1	_Test_f417f1	Task	1	0	10	1
Task-_Test_f4a608	_Test_f4a608	Task	1	0	10	1
Task-_Test_f635dc	_Test_f635dc	Task	1	0	10	1
Task-_Test_f6b412	_Test_f6b412	Task	1	0	10	1
Task-_Test_f7def2	_Test_f7def2	Task	1	0	10	1
Task-_Test_fab835	_Test_fab835	Task	1	0	10	1
Task-_Test_fbd335	_Test_fbd335	Task	1	0	10	1
Task-_Test_fc193d	_Test_fc193d	Task	1	0	10	1
Task-_Test_ff0556	_Test_ff0556	Task	1	0	10	1
User Scope Context-_Test_665254	_Test_665254	User Scope Context	1	0	10	1
User Scope Context-_Test_fdb7f7	_Test_fdb7f7	User Scope Context	1	0	10	1
```
