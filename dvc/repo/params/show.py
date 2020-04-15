import yaml
import logging

from dvc.repo import locked
from dvc.path_info import PathInfo
from dvc.compat import fspath_py35
from dvc.exceptions import DvcException
from dvc.dependency.param import DependencyPARAMS


logger = logging.getLogger(__name__)


class NoParamsError(DvcException):
    pass


def _collect_configs(repo):
    configs = set()
    configs.add(PathInfo(repo.root_dir) / DependencyPARAMS.DEFAULT_PARAMS_FILE)
    for stage in repo.stages:
        for dep in stage.deps:
            if not isinstance(dep, DependencyPARAMS):
                continue

            configs.add(dep.path_info)
    return list(configs)


def _read_params(repo, configs, rev):
    res = {}
    for config in configs:
        if not repo.tree.exists(fspath_py35(config)):
            continue

        with repo.tree.open(fspath_py35(config), "r") as fobj:
            try:
                res[str(config)] = yaml.safe_load(fobj)
            except yaml.YAMLError:
                logger.debug(
                    "failed to read '%s' on '%s'", config, rev, exc_info=True
                )
                continue

    return res


@locked
def show(repo, revs=None):
    res = {}

    for branch in repo.brancher(revs=revs):
        configs = _collect_configs(repo)
        params = _read_params(repo, configs, branch)

        if params:
            res[branch] = params

    if not res:
        raise NoParamsError("no parameter configs files in this repository")

    # Hide working tree params if they are the same as in the active branch
    try:
        active_branch = repo.scm.active_branch()
    except TypeError:
        pass  # Detached head
    else:
        if res.get("working tree") == res.get(active_branch):
            res.pop("working tree", None)

    return res