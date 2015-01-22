from mercurial import error
from mercurial import extensions
from mercurial import util
from mercurial.i18n import _
from mercurial.lock import release

try:
    histedit = extensions.find('histedit')
except KeyError:
    histedit = None

histedit_editcomment = """# Edit history between %s and %s
#
# Commits are listed from least to most recent
#
# Commands:
#  p, pick = use commit
#  r, reword = use commit, but edit commit message
#  e, edit = use commit, but stop for amending
#  s, squash = use commit, but combine it with the one above
#  f, fixup = like squash, but discard this commit's description
#
# If you remove a line here THAT COMMIT WILL BE LOST.
#
# However, if you remove everything, the histedit will be aborted.
"""

histedit_actiontable = {
    'p': histedit.pick,
    'pick': histedit.pick,
    'r': histedit.message,
    'reword': histedit.message,
    'e': histedit.edit,
    'edit': histedit.edit,
    's': histedit.fold,
    'squash': histedit.fold,
    'f': histedit.rollup,
    'fixup': histedit.rollup,
    'd': histedit.drop,
    'drop': histedit.drop
}


def histedit_verifyrules(rules, repo, ctxs):
    """Verify that there exists exactly one edit rule per given changeset.

    Will abort if there are too many or no rules, a malformed rule,
    or a rule on a changeset outside of the user-given range.
    """
    parsed = []
    expected = set(str(c) for c in ctxs)
    seen = set()
    for r in rules:
        if ' ' not in r:
            raise util.Abort(_('malformed line "%s"') % r)
        action, rest = r.split(' ', 1)
        ha = rest.strip().split(' ', 1)[0]
        try:
            ha = str(repo[ha])  # ensure it's a short hash
        except error.RepoError:
            raise util.Abort(
                _('unknown changeset %s listed') % ha)
        if ha not in expected:
            raise util.Abort(
                _('may not use changesets other than the ones listed'))
        if ha in seen:
            raise util.Abort(_('duplicated command for changeset %s') % ha)
        seen.add(ha)
        if action not in histedit_actiontable:
            raise util.Abort(_('unknown action "%s"') % action)
        parsed.append([action, ha])

    missing = sorted(expected - seen)  # sort to stabilize output
    if not seen:
        raise util.Abort('nothing to do')
    for m in missing:
        parsed.append(['drop', m])

    return parsed


def histeditcommand(ui, repo, *freeargs, **opts):
    state = histedit.histeditstate(repo)
    try:
        state.wlock = repo.wlock()
        state.lock = repo.lock()
        histedit._histedit(ui, repo, state, *freeargs, **opts)
    finally:
        release(state.lock, state.wlock)


def extsetup(ui):
    if histedit:
        oldhistedit = histedit.cmdtable['histedit']
        histedit.cmdtable['histedit'] = (histeditcommand, oldhistedit[1], oldhistedit[2])
        histedit.editcomment = histedit_editcomment
        histedit.actiontable = histedit_actiontable
        histedit.verifyrules = histedit_verifyrules
