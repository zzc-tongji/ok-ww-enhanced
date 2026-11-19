---
name: merge-upstream
description: Synchronize upstream/master and origin/main, mirror master and tags to origin, merge the latest strictly three-part stable vMAJOR.MINOR.PATCH tag into main, and publish its rc.0 tag. Stop immediately if that rc.0 tag already exists; require human review after resolving any non-catalog conflict. Use for requests such as "merge upstream", "sync upstream", "update upstream", "pull upstream changes", "merge latest upstream release", "同步上游", "合并上游", "更新上游", "拉取上游更新", "更新原版", "同步原版", or "合并原版更新".
---

# Merge Upstream

Run this workflow from the repository root. Use `upstream/master` as the original project's source and `origin/main` as the enhanced project's integration branch. Mirror the local `master` branch to `origin/master`.

Execute commands individually and check every exit status. Stop on failure unless the failure is the expected merge-conflict exit handled below. Never force-push, reset user changes, automatically stash, rewrite tags, or silently replace either side of a conflict.

## 1. Preflight, Fetch, and Duplicate-Release Gate

1. Inspect `git status --short --branch`, `git remote -v`, branch tracking, and any in-progress Git operation. Verify that `origin` and `upstream` identify the intended enhanced and original repositories.
2. For a fresh run, require a clean index and working tree and no pending merge, rebase, or cherry-pick. Stop and report unexpected local changes; do not commit them automatically. For a resumed run, first follow **Resume After Human Review** instead of rejecting the expected pending merge.
3. Fetch every remote and all tags before selecting a release:

   ```powershell
   git fetch --all --prune --tags
   ```

   Use this explicit spelling rather than `git fetch -ap`: `-a` means append to `FETCH_HEAD`, not fetch all remotes, and `-p` does not fetch all tags. Do not use `--prune-tags` or force-fetch conflicting tags. Stop if fetching fails.
4. Select the highest numeric version among tags matching **exactly** `^v[0-9]+\.[0-9]+\.[0-9]+$`. Use escaped literal dots, case-sensitive matching, and absolute start/end anchors. Ignore every suffix, prefix, extra component, and prerelease; do not choose by creation date or lexicographic order.

   ```powershell
   $MergedTag = git tag --list --sort=-version:refname |
     Where-Object { $_ -cmatch '\Av[0-9]+\.[0-9]+\.[0-9]+\z' } |
     Select-Object -First 1
   if ($LASTEXITCODE -ne 0) { throw 'Cannot list tags.' }
   if (-not $MergedTag) { throw 'No strictly three-part stable release tag exists.' }
   $RcTag = "$MergedTag-rc.0"
   git show-ref --verify --quiet "refs/tags/$RcTag"
   $TagStatus = $LASTEXITCODE
   ```

   For example, accept `v1.2.3` and prefer `v1.10.0` over `v1.9.9`; reject `v1.2.3-rc.0`, `v1.2.3-beta`, `v1.2.3+build`, `v1.2`, `v1.2.3.4`, `V1.2.3`, and `v1x2x3`.
5. **If `$TagStatus` is 0, end execution immediately.** Report the selected stable tag, the existing exact `$RcTag`, and that synchronization was skipped. A matching local tag or a tag fetched from any remote counts, even if it points elsewhere. Do not pull branches, merge, commit, push, wait, fall back to an older stable tag, or increment to `rc.1`. If the status is neither 0 nor 1, stop and report the Git error.
6. Keep the selected tag and its peeled commit SHA fixed for this run. If resuming a checkpoint and the newly selected tag differs from the recorded tag, stop for user direction rather than changing the pending merge target.

## 2. Update Both Branches and Mirror Master

Only continue after the duplicate-release gate passes. Create missing local branches from the corresponding remote-tracking branches; do not recreate or reset existing branches.

```powershell
git switch master
git pull --ff-only --tags upstream master
git switch main
git pull --ff-only --tags origin main
git switch master
git push origin master
git push origin --tags
git switch main
```

Check each command before executing the next. Before pushing `master`, verify it matches `upstream/master`; if it contains local-only commits, stop rather than publishing unrelated history. On divergence or a rejected push, stop and report the issue without rebasing or forcing. Use `--tags` as the full spelling of the requested tag push.

Before starting the merge, record a local JSON checkpoint at the path returned by `git rev-parse --git-path merge-upstream-state.json`. Do not add it to Git. Store the repository identity, selected stable tag and peeled SHA, intended rc tag, pre-merge `main` HEAD, current phase, and original conflict paths once known. Update the checkpoint after each completed phase so a later conversation can inspect actual progress rather than repeat publishing operations.

## 3. Merge the Selected Stable Tag

```powershell
git merge --no-commit --no-edit "$MergedTag"
```

Allow a fast-forward when applicable. For a non-fast-forward merge, `--no-commit` keeps completion under this workflow's control. If Git reports an error without unmerged paths or a pending merge, stop rather than treating it as a conflict.

Immediately capture the original conflict list using `git diff --name-only --diff-filter=U` and save it in the checkpoint **before** resolving or staging anything. Classify normalized repository-relative paths using the case-sensitive pattern `\Ai18n/(?:[^/]+/)+LC_MESSAGES/ok\.po\z`, equivalent to `i18n/**/LC_MESSAGES/ok.po` with a locale directory.

- **No conflicts:** Run appropriate checks for the incoming changes. If `MERGE_HEAD` exists, finish with `git commit -m "Merge upstream release $MergedTag into main"`. A fast-forward needs no extra commit. If the tag is already an ancestor of `main` but no rc.0 exists, do not manufacture an empty merge; verify ancestry and continue with the current `main` commit.
- **Only matching `ok.po` conflicts:** Follow `.agents/skills/ok-script-i18n/SKILL.md`. Once that skill's workflow succeeds, finish the merge commit and continue automatically.
- **Any other conflicted path:** Follow **Mixed or Non-Catalog Conflicts**. This includes an `ok.mo` conflict, any other file under `i18n`, and any path outside the exact catalog pattern. Classify using the original conflict list, not the list remaining after repairs.

### Mixed or Non-Catalog Conflicts: Mandatory Review Stop

1. Inspect the base, local, and upstream versions. Attempt targeted repairs that preserve enhanced functionality while integrating the upstream release. Load relevant repository development skills for affected code. Resolve any catalog conflicts by following `.agents/skills/ok-script-i18n/SKILL.md` too.
2. Run focused checks with the repository-local Python interpreter where applicable. Stage only intended resolved files. Preserve the original conflict list even when every path is now resolved.
3. **Do not finalize the merge in this conversation.** Do not run another `git merge`, `git merge --continue`, or `git commit`; do not push `main`, create or push the rc tag, or run the final wait/pull. Leave `MERGE_HEAD` and the resolved index intact for review. Do not abort the merge automatically.
4. Mark the checkpoint `awaiting-human-review`. Report every original non-catalog conflict by exact path, what conflicted, how it was repaired, the behavior preserved or changed, checks and results, and remaining uncertainties or unresolved paths. Include the selected tag, pre-merge HEAD, current branch, and confirmation that the merge is still uncommitted. Clearly state that `master` and upstream tags may already have been pushed in step 2.
5. Ask the user to review and approve completion **in a subsequent conversation turn**, then stop execution. The original synchronization request is not approval of the repairs. If a repair is unsafe, leave it unresolved and explain the blocker instead of guessing.

### Resume After Human Review

- Read the checkpoint and inspect `git status`, `MERGE_HEAD`, the current branch, staged/unstaged diffs, and the prior review report before any switch or pull. Do not rerun the fresh-run branch-update sequence with a pending merge.
- Perform the safe fetch and duplicate-release gate from step 1 without switching branches. If the exact rc.0 tag now exists, stop immediately even on a resumed run, and explain that the pending local merge has been left untouched.
- Require explicit approval in a later turn of the reported non-catalog repairs. If approval is absent, show the pending review state and stop. If the target, repository, or reviewed changes have changed unexpectedly, request a new review rather than assuming the old approval applies.
- Verify `main` is checked out, the recorded upstream commit matches `MERGE_HEAD`, no unmerged paths remain, and staged content contains only intended merge results. Rerun relevant validation, following `.agents/skills/ok-script-i18n/SKILL.md` for catalog changes. Stage any explicitly reviewed follow-up repairs.
- After approval and successful validation, finish the existing merge with `git commit -m "Merge upstream release $MergedTag into main"`; do not start another merge. If a human already committed it, verify that the recorded pre-merge HEAD and selected tag commit are ancestors of the current `main`, that the reviewed resolution is present, and that no operation remains pending before continuing.
- Resume at the first incomplete phase below after verifying its Git state. Never infer approval or completion from a checkpoint alone.

## 4. Push Main

Require a completed merge or verified fast-forward, a clean working tree, and the selected stable tag's peeled commit as an ancestor of `main`.

```powershell
git push origin main
```

On rejection, stop without forcing, creating a tag, or claiming success. Record the successfully pushed commit SHA in the checkpoint.

## 5. Create and Push the rc.0 Tag

Recheck the exact `$RcTag` locally and on `origin` immediately before creation to catch concurrent publication. If it now exists, stop and report it; do not overwrite it or continue with another number. If the remote lookup fails, stop rather than interpreting the failure as absence.

Create an annotated tag on the `main` commit successfully pushed in step 4, then push tags:

```powershell
git tag -a "$RcTag" -m "$RcTag" "<successfully-pushed-main-sha>"
git push origin --tags
```

Substitute the recorded commit SHA for the placeholder. Verify both command results and confirm that the remote tag peels to the intended commit. If tag creation succeeds but pushing fails, report the partial state and leave the tag untouched. Never automatically delete or recreate it on retry: the existing-tag gate still applies.

## 6. Wait for Generated Diff Reports and Refresh Main

Only after successful branch and tag publication, wait **120 seconds**, then pull `main` from `origin`:

```powershell
Start-Sleep -Seconds 120
git pull --ff-only origin main
```

Use a sufficient tool timeout or a non-polling delayed command so the wait actually finishes before pulling. Keep `main` checked out and the working tree clean. Inspect `.github/workflows/diff_reports.yaml` or the workflow run when needed: it can generate an additional commit on `main`. Do not move the rc tag to that later generated commit.

Verify the pull succeeded and that local `main` matches the fetched `origin/main`. If the workflow is still running, fetch/pull again after it finishes before claiming the generated reports are current. Do not manufacture a report commit when no reports changed. If CI status cannot be verified, report that limitation rather than promising that all generated commits have arrived.

Mark the checkpoint complete only after the final refresh succeeds. Report the merged stable tag, rc.0 tag and commit, pushed branches/tags, conflict handling or prior approval, final `main` commit, and final pull/CI status. Distinguish completed publication from a failed or still-pending post-publication refresh.
