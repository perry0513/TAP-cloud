# Rebuilding the UCLID5 proof for the un-fused model

**Branch:** `stap-content-binding-tags`. **Date:** 2026-08-27.
Companion to `docs/uclid-model-and-proof-plan.md`, which is the plan this
implements. Where the two disagree, this document is what was actually built.

---

## 1. What changed in the model

| change | file |
|---|---|
| Tags commit to content: `t' = chain(t, mem, av)`, with left inverses `tag_prev`, `tag_mem`, `tag_valid_map`, and `rank` for the freshness order | `modules/ap-types.ucl` |
| `storePS` computes the tag *after* assembling the ciphertext, and normalizes untouched addresses to a blank value so the tag is a function of what was stored | `modules/tap-mod-store-storage.ucl` |
| `updateTag` is a conditional append: it commits only if `tag_prev(Mtag) == KMStag` | `modules/tap-mod-kms.ucl` |
| `create_key` issues a key unrelated to anything already in the system, archives included | `modules/tap-mod-kms.ucl` |
| `tamperPS` restated for chained tags, and the blob it writes is tagged consistently with its own content | `modules/tap-mod-tamper-storage.ucl` |
| New adversary operations `archiveStorage` / `replayStorage`: one retained ciphertext the adversary can reinstall at any later point | `modules/tap-mod-archive-storage.ucl` |
| `getKeyTag` and `updateTag` become enclave instructions; `storePS`/`loadPS` name the granular operations | `proofs/proof-common.ucl`, `modules/tap-mod.ucl` |

The last row is the one that removes assumption A1. It was previously enforced
in two places that had drifted apart: `proof-common.ucl` and a second copy of
`tap_proof_op_valid_in_enclave` inside `tap-mod.ucl`. Only the first was
commented; the second silently kept the granular operations out, which is why
`e-get-key-and-tag.ucl` and `e-update-tag.ucl` were passing vacuously.

## 2. Why the tag carries the ciphertext rather than a digest of it

The plan proposed `chain(t, digest(m, av))` with `digest` injective. The
mechanization uses `chain(t, m, av)` with projections `tag_mem` and
`tag_valid_map`. The two are equivalent as idealizations, but the second makes
the step the proof leans on hardest --

> equal tags carry equal ciphertexts

-- a matter of congruence (`tag_mem(t1) == tag_mem(t2)` when `t1 == t2`) rather
than of instantiating an injectivity axiom quantified over array sorts.

## 3. The harness: what the reference trace does

This is the substantive design decision, and it is not what the plan proposed.

**The plan** had trace 2 stutter at `storePS` and perform a fused
store-and-commit at trace 1's `updateTag`. That leaves trace 1's program counter
one instruction ahead of trace 2's for the whole window, which breaks the
program-counter half of the property being proved, and it requires trace 2 to
reproduce a store from register and memory state it can no longer read.

**What is built** instead: the two traces run `storePS` and `updateTag` in
lockstep, and trace 2 **discards its uncommitted write when the enclave that
wrote it is destroyed**:

```
if (current_mode == mode_untrusted && r_proof_op == tap_proof_op_destroy &&
    r_eid == eid && phase == ph_pending && status_1' == enclave_op_success) {
  call (discard_status') = cpu_2.rollback_storage(eid);
}
```

The justification is that trace 2 tracks the *committed* history. A write whose
commit can no longer happen is not part of that history. Leaving it in place
would strand trace 2 holding a ciphertext whose tag the KMS has never seen, so
trace 2's own load would abort after the relaunch -- and `trace_2_no_abort` is
one of the things being proved.

This does mean trace 2 is no longer literally "the same platform with the
adversary's steps deleted": on a destroy inside the window it performs one
operation trace 1 does not. It agrees with the golden trace at every labelled
step, which is all the reduction uses, but that agreement is a lemma about the
harness and it is **not mechanized**. It is the adequacy lemma of
`docs/uclid-model-and-proof-plan.md` §IV.3, and it should go in the paper.

As stated there, the lemma is **false at repeated labels** -- see §B, which also
says what would repair it.

## 4. The phase automaton

`loaded`/`stored` are replaced by `phase : {ph_syncing, ph_active, ph_pending,
ph_dead}` plus `key_fetched`. The scheduling assumptions are the operational
form of the session grammar:

```
getKeyTag  requires  ph_syncing && !key_fetched
loadPS     requires  ph_syncing && key_fetched && already_stored
compute    requires  ph_active
storePS    requires  ph_active
updateTag  requires  ph_pending
```

`!key_fetched` on `getKeyTag` is load-bearing: a mid-session re-read of the KMS
tag abandons a pending store just as a crash does, and that is the crash-free
variant of the tag-reuse attack.

`already_stored`, `kms_key_deleted`, `kms_storage_key_sync` and
`kms_storage_tag_sync` stopped being ghosts and became macros over trace 1's
state. Splitting one operation into two moves the point at which storage and
the KMS agree, and hand-maintained flags are exactly what goes stale when that
happens.

## 5. Invariants that were false in the new model, not merely unproven

- **`abort_implies_tamper`** -- deleted. An enclave can abort for an untampered
  reason (it returns from a crash, finds a ciphertext whose tag was never
  committed, and halts), and the adversary can afterwards roll that ciphertext
  back so storage and the KMS agree again. The abort is sticky; its cause is
  not recoverable from the state.
- **`possible_states`** -- the old form claimed nothing is stored before the
  first commit. `storePS` writes a ciphertext under the client key before any
  `updateTag` has succeeded, so that is false.
- **`kms_storage_same_tag_2`**, **`enc_storage_same_tag_1`** -- true outside the
  window only.
- **`storage_same_mem` / `storage_same_addr_valid`** -- re-stated as consequences
  of tag equality, which is what content binding actually buys. Under the old
  guard (`already_stored && kms_storage_tag_sync`) they are false, because a
  replay of the committed ciphertext during the window satisfies the guard while
  the two traces hold different ciphertexts.

## 6. Invariants that are now definitional

Because the four flags became macros over trace 1's state, these carry no
content any more: `kms_tag_valid_1`, `kms_tag_invalid_1`,
`kms_storage_same_key_1`, `kms_storage_same_tag_1`, `kms_storage_key_unsync`,
`kms_storage_tag_unsync`, `key_deleted_implies_invalid`, `possible_states`. The
content they used to carry -- that the ghost tracked the state -- is now true by
construction. The work moved into the new invariants (§7).

## 7. New invariants

**Content binding.** `fresh_binds_1/2`, `stale_binds_1/2`, `archive_binds_1`:
every reachable ciphertext, in either storage slot or in the adversary's
archive, is the one its tag names.

**Cross-trace tag agreement.** `kms_tag_same`, `enc_tag_same`, `synced_tag_1/2`
(outside the window the enclave's tag is the committed tag), `pending_chains_1/2`
(inside the window it chains directly from it -- this is what makes the
conditional append accept the commit rather than abort).

**Key provenance.** `client_key_1`: if the key the KMS currently holds turns up
in either storage slot or in the archive, then the enclave is holding that key.
Without it a replay could reinstall a ciphertext under the current key while the
enclave still held an older one.

**Window shape.** `pending_stale_2`: inside the window the reference trace's
`stale` slot is exactly the committed ciphertext, which is what makes the
discard of §3 possible at all.

## 8. What is still not proven

- **Theorem 2 (the reduction)** is paper-level. The harness checks the reduced
  property; that this implies generalized integrity is the triangle argument,
  and it is not mechanized.
- **The harness adequacy lemma** (§3) is not mechanized.
- **The adversary's archive holds one ciphertext.** The tag-reuse attack needs
  only one, but the theorem is against an adversary that retains one, not an
  unbounded set.
- **`rollbackStorage` is still limited to one occurrence per trace**
  (`assume (r_proof_op == rollback_storage ==> !storage_rolledback)`, inherited).
  `replayStorage` has no such limit, but it can only reinstall what
  `archiveStorage` copied out of `fresh`, so it does not subsume rollback.
- **`tamperStorage` writes a blob under a non-client key** with a tag excluded
  from what the enclave would accept. The exclusions do not weaken the adversary
  in a way that could hide an attack -- a blob under a non-client key is rejected
  by `loadPS` on the key check regardless of its tag -- but they are assumptions
  about the encryption, not consequences of anything proved.
- **Cache and page-table confidentiality** are still not proved for the storage
  operations, unchanged from before.

---

## 9. Results

All runs use `cvc5 -q --lang smt2 --force-logic=ALL`. `unknown` is counted as a
failure throughout, never as a pass.

| proof | case splits | obligations | sat | unknown |
|---|---|---|---|---|
| `tap` module (CPU + operations) | -- | 6130 | 0 | 0 |
| Secure measurement | -- | 287 | 0 | 0 |
| Generalized (reduced) integrity | 23 | 5728 | 0 | 0 |
| Memory confidentiality | 23 | 5240 | 0 | 0 |

The integrity case splits are the seven enclave instructions (`compute`, `exit`,
`pause`, `storePS`, `loadPS`, `getKeyTag`, `updateTag`) and sixteen adversary
operations, including `replayPS`.

## 10. Vacuity

An operation that the scheduling assumptions make unreachable verifies for free,
and a contradictory set of axioms or initial assumptions makes everything verify
for free. The two case splits for `getKeyTag` and `updateTag` in the previous
version of this proof were unreachable, so these checks matter.

**Axioms and initial state.** `assert(false)` at the end of an init block. `unsat`
would mean the init assumptions together with the global axioms are
contradictory.

| probe | result |
|---|---|
| integrity init (`integrity-proof-init.ucl`) | not refuted -- init satisfiable, axioms consistent |
| confidentiality init (`mem-conf-proof-init.ucl`) | not refuted -- init satisfiable, axioms consistent |

This is the check that the new axioms -- the `chain` projections, `rank`, and the
null-tag bindings -- are consistent, and that adding them did not collapse the
model.

**Transition relation.** `assert(false)` (with an optional extra assumption) in
the proof's `next` block.

| probe | result |
|---|---|
| `enc-getkeytag`, `enc-store`, `enc-load`, `enc-updatetag` | reachable |
| `adv-createkey` | reachable |
| `adv-destroy` with `phase == ph_pending` | reachable |
| `adv-rollback` with `phase == ph_pending` | reachable |
| `adv-replay` in the window, replaying the committed tag | reachable |
| conf `e-getkeytag`, `e-updatetag`, `replay-storage` | reachable |

The window probes matter most: they say the store/commit window is genuinely
reachable at a destroy, at a rollback, and at a replay, so the crash-in-window
scenarios are being checked rather than assumed away.

**Module procedures.** `assert(false)` on the success path of `_store_storage`,
`update_tag` and `replay_storage`: no `unsat`, so none of those paths is
provably unreachable and the procedure contracts are not vacuous.

## 11. Are content-binding tags load-bearing?

`proofs/regression/` holds a variant in which `chain` depends only on its
predecessor -- a counter, expressed in the current framework -- with the content
projections and the five binding invariants removed. Everything else is
identical. (The variant was built against the single-slot archive that preceded
the replay history of appendix A; it keeps that archive, since without content
binding the history cannot be represented by tags alone.)

- `enc-load` still passes (242 unsat). A load does not write storage, so nothing
  there needs the tag to bind content.
- **`adv-replay` fails**, on exactly two obligations:
  `storage_same_mem` and `storage_same_addr_valid`. Neither is provable by cvc5
  (with or without `--enum-inst`) or by z3.

That is the tag-reuse attack, located precisely: with a position-only tag the
adversary can reinstall an archived ciphertext whose tag matches the committed
tag but whose content is a discarded attempt, and the two traces' storage
diverges. With a content-binding tag the antecedent forces the contents equal.

Note what this does and does not show. It shows the proof *breaks* at that step
without content binding, on the property that carries the security guarantee. It
is not a reachability witness for the attack: that would need a bounded model
check, which is not built here.

---

# Appendix — replacing the archive with an unbounded replay history

Not implemented on this branch. Spiked on `spike-produced-ledger` (see §A.4).

## A.1 The problem this solves

The archive built above holds **one** ciphertext. The tag-reuse attack needs
exactly two retained at once -- the committed one to restore after the crash, and
the discarded attempt to replay later -- so today `rollbackPS` supplies one (via
`stale`) and the archive the other. That is enough to express the attack, but it
is not the real adversary, and the paper says so itself (§5, "Persistent
Storage"):

> In reality, PS may store multiple ciphertexts for each enclave and the attacker
> may keep the entire history of ciphertexts which enclaves have stored in PS to
> later perform rollback attacks. We justify that this simplified model is sound
> as it captures the attacks of interest on PS: [...] using any stale ciphertexts
> to perform rollback attack is no different than using the single stale version
> PSstale[e].

The second clause is false, and the tag-reuse attack is the counterexample: the
ciphertext it replays is neither `fresh` nor `stale` at the moment of the replay,
having been evicted by the intervening store. So the abstraction carries a
soundness obligation that cannot be discharged.

## A.2 The design

Track the history explicitly, as tags:

```
tap_storage_produced     : [tap_enclave_id_t][tag_t]boolean
tap_storage_produced_key : [tap_enclave_id_t][tag_t]key_t
```

| operation | effect |
|---|---|
| `storePS` | as before, plus `produced[e][t'] := true`, `produced_key[e][t'] := Mkey` |
| `loadPS` | unchanged |
| `replayPS(e, t)` | requires `produced[e][t]`; installs `(tag_mem(t), tag_valid_map(t), produced_key[e][t], t)` |
| `tamperPS` | unchanged |
| `archivePS` | **gone** |

Recording only tags loses nothing. `storePS` computes
`t' = chain(Mtag, m, av)` *from* the ciphertext it has just assembled, and the
projection axioms invert it:

```
axiom (forall t, m, av :: tag_mem(chain(t, m, av))       == m);
axiom (forall t, m, av :: tag_valid_map(chain(t, m, av)) == av);
```

so `tag_mem(t')` **is** the stored array and `tag_valid_map(t')` **is** the
stored address set -- equal by the axiom instantiated at that store, not merely
determined. The set of ciphertexts the enclave ever produced is therefore in
bijection with the set of tags it ever produced, and the ledger is a change of
representation rather than an approximation. This works *only* because tags bind
content; in the position-only variant of `proofs/regression/` the ledger would
have to store ciphertexts.

The key is the one component a tag does not determine, so it gets a companion
map. Putting the key inside `chain` would be more faithful to a hash of the
ciphertext, but it breaks `enc_tag_same`: after `delete_key` + `create_key` the
two traces hold different keys (trace 2 does not step on key operations), and in
the bootstrap case -- nothing committed, so no load intervenes to catch the
divergence -- both reach a `storePS` and would compute different tags for equal
content.

## A.3 What becomes redundant

`PS_stale[e]` exists only as the source for `rollbackPS`. Its value is always the
previous `PS_fresh`, written by some earlier `storePS`, so its tag is in
`produced`, and

```
rollbackPS(e)  ==  replayPS(e, tag(PS_stale[e]))
```

Two checks that dropping the slot loses nothing. Tampered content does reach
`stale` (a `tamperPS` followed by a `storePS` shifts it there), but `rollbackPS`
requires `fresh.key == stale.key` and the tampered blob carries a non-client key,
so it was never rollback-able: `stale`'s *usable* values are exactly produced
ciphertexts. And a second slot adds no adversary power, because the adversary's
only lever is what sits in PS when the enclave loads.

So PS collapses to `PS : Eid -> ciphertext`, and `rollbackPS` goes with the slot
-- taking with it the inherited `!storage_rolledback` cap, which limits the
adversary to one rollback per trace for no principled reason.

The harness improves too. Trace 2's discard at a destroy currently calls
`rollback_storage`, which means "go back one version" and has an awkward rank-0
failure case. It becomes "restore the committed ciphertext" --
`tag_mem(KMStag[e])` -- which is what it means and is well-defined from the KMS
tag alone.

## A.4 Spike result

The risk was `client_key_1`: its archive disjunct is one array read today and
becomes a quantifier over produced tags, and `create_key` has to exclude an
unbounded set of historical keys rather than one archive entry. The specific
hazard was that `create_key`'s exclusion might be *unsatisfiable*, which would
make its success branch unreachable and every obligation about it vacuous.

Spiked on `spike-produced-ledger`, keeping `fresh`/`stale` so the change stays
contained. `client_key_1` splits in two:

```
invariant client_key_1:                       // storage slots, as before minus the archive
  (verif && key_fetched && valid_key(kms_key)) ==>
    ((fresh.key == kms_key || stale.key == kms_key) ==> Mkey == kms_key);

invariant client_key_produced_1:              // the replay history
  (verif && key_fetched && valid_key(kms_key)) ==>
    (forall (t : tag_t) ::
      (produced[eid][t] && produced_key[eid][t] == kms_key) ==> Mkey == kms_key);
```

Stated as a universal over tags rather than an existential in the antecedent, so
the solver gets a trigger on `produced[eid][t]`.

**Everything passed, first attempt, with no auxiliary invariants.**

| check | result |
|---|---|
| `make tap-printed` | 6130 unsat, 0 sat, 0 unknown |
| `adv-replay` | 240 unsat |
| `adv-createkey` | 242 unsat |
| `enc-store` | 248 unsat |
| `adv-destroy` / `adv-rollback` / `adv-tamper` | 244 / 240 / 240 unsat |
| `enc-load` / `enc-updatetag` / `enc-getkeytag` | 252 / 236 / 236 unsat |
| vacuity: `create_key` success branch (module) | 8 obligations, **0 unsat** -- reachable |
| vacuity: `adv-createkey` | reachable |
| vacuity: `adv-replay` in the window, replaying the committed tag | reachable |

Why the invariant is easy: at a `storePS` the new entry's key is `Mkey`. If
`Mkey == kms_key` the consequent holds directly; otherwise the new entry fails
the antecedent and older entries are covered by instantiating the pre-state
universal at the same `t`. E-matching on `produced[eid][t]` finds that without
help. And `archive_binds_1` could be **deleted**: a replay installs `tag_mem(t)`
by construction, so `fresh_binds_1` holds there without induction.

**Not covered by the spike:** the other fifteen integrity case splits (they touch
`produced` only through the shared invariant); the confidentiality proof, which
still references the archive variables and does not compile on that branch; the
measurement proof; and the `fresh`/`stale` removal of §A.3, which is the large
part of the refactor.


---

# Appendix B — labelling discarded work (suggestion, NOT adopted)

Recorded for later. The labelling function is unchanged on this branch and the
proofs do not depend on this.

## B.1 What the current labelling does at a crash

A crash makes a label repeat. From the definition,

```
L_π(i) = ⊥          if ¬valid(π^i) ∨ syncing(π^i)      ← the relaunch prefix
         (x, 0)     else if synced(π^i)                ← x is the last non-⊥ label,
                                                          i.e. the pre-crash (x, k)
         (x, y + 1) else if π^i computes               ← (x,1), (x,2), … again
```

so the computes of a discarded attempt and the computes of the attempt that
replaces it carry the same labels.

## B.2 Consequence

`InpEq` is a whole-trace premise, not a per-pair guard:

```
∀π₁, π₂. E_e(π₁⁰) = E_e(π₂⁰) ∧ InpEq(π₁, π₂) ⇒ StateOutEq(π₁, π₂)
   where  InpEq(π₁, π₂) := ∀i, j. H(i,j) ⇒ … same inputs …
```

`H` is label equality, so if π revisits a label and π* has one step there,
alignment relates *both* π-steps to that single π*-step and `InpEq` forces them
to carry the same input. A single mismatch makes `InpEq` false, which makes the
implication vacuous **for the whole trace pair** -- not just at the offending
step.

The case that matters is not adversarial:

```
client sends a1  →  enclave computes d₁, stores, crashes before the commit
client sends a2  →  enclave reloads d, computes d₂ = δ(d, a2), stores, commits
```

Ordinary operation, and exactly what the system exists to survive. Under the
current labelling `InpEq` fails and generalized integrity says nothing about this
execution -- including every later rank.

The tag-reuse attack is still covered, but only in a length-asymmetric form:
attempt 1 runs one compute, attempt 2 runs two, the shared `(x,1)` carries the
same input in both, and the violation appears at `(x+1,0)`. That is the realistic
shape (a crash is asynchronous), so the attack is not lost -- but it survives by
an accident of trace shape rather than because the definition covers it.

## B.3 The suggested change

Send discarded computes to `⊥`:

```
committed(π^i) ≜ ∃ j > i.  commits(π^j)  ∧  e is not destroyed in (i, j]

L_π(i) = … (x, y + 1)  else if π^i computes ∧ committed(π^i)
           ⊥           else if π^i computes
```

Then labels never repeat within a trace, `InpEq` imposes nothing across a crash,
and no comparison is demanded at a discarded step -- which is the intent.

Formally this **weakens the antecedent** (fewer `InpEq` conjuncts, so strictly
more executions are in scope) and **weakens the conclusion only at discarded
steps** (guarantees that were never wanted and are unobtainable anyway). The
Coverage Lemma gets easier, since π has fewer labels for π* to cover, and the
triangle proof chains labels exactly as before.

The look-ahead in `committed` costs nothing: `L_π` is a function of the whole
trace, so a retrospective condition is ordinary mathematics. A prophecy variable
would only be needed to *simulate* such a labelling step by step inside a
transition system, and the harness never simulates the labelling -- it proves the
reduced property operationally.

## B.4 It also repairs the adequacy lemma

§3 states the harness adequacy lemma as

> for every step of `ρ` carrying a label `ℓ ≠ ⊥`, `E_e` of `ρ` at that step
> equals `E_e(π*^k)` for the step `k` of π* carrying `ℓ`

which is **false as written**: if `ρ` visits `(x,1)` twice with different inputs,
its states differ at the two visits while π* has one step at `(x,1)`. With
discarded computes at `⊥` the pre-crash visit drops out and the lemma holds. The
harness's discard of uncommitted work at a destroy (§3) is the operational
counterpart of the same idea, so the two line up instead of needing to be
reconciled.

## B.5 If the labelling is kept

Then the restriction belongs in the theorem statement rather than buried in
`InpEq`:

> Integrity is guaranteed for executions in which the client re-issues the same
> inputs at the same offsets after a crash.
