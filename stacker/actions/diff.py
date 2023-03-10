import logging
from operator import attrgetter

from .base import plan, build_walker
from . import build
from .. import exceptions
from ..status import (
    NotSubmittedStatus,
    NotUpdatedStatus,
    COMPLETE,
    INTERRUPTED,
)

logger = logging.getLogger(__name__)


class DictValue(object):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"
    UNMODIFIED = "UNMODIFIED"

    formatter = "%s%s = %s"

    def __init__(self, key, old_value, new_value):
        self.key = key
        self.old_value = old_value
        self.new_value = new_value

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def changes(self):
        """Returns a list of changes to represent the diff between
        old and new value.

        Returns:
            list: [string] representation of the change (if any)
                between old and new value
        """
        output = []
        if self.status() is self.UNMODIFIED:
            output = [self.formatter % (' ', self.key, self.old_value)]
        elif self.status() is self.ADDED:
            output.append(self.formatter % ('+', self.key, self.new_value))
        elif self.status() is self.REMOVED:
            output.append(self.formatter % ('-', self.key, self.old_value))
        elif self.status() is self.MODIFIED:
            output.append(self.formatter % ('-', self.key, self.old_value))
            output.append(self.formatter % ('+', self.key, self.new_value))
        return output

    def status(self):
        if self.old_value == self.new_value:
            return self.UNMODIFIED
        elif self.old_value is None:
            return self.ADDED
        elif self.new_value is None:
            return self.REMOVED
        else:
            return self.MODIFIED


def diff_dictionaries(old_dict, new_dict):
    """Diffs two single dimension dictionaries

    Returns the number of changes and an unordered list
    expressing the common entries and changes.

    Args:
        old_dict(dict): old dictionary
        new_dict(dict): new dictionary

    Returns: list()
        int: number of changed records
        list: [DictValue]
    """

    old_set = set(old_dict)
    new_set = set(new_dict)

    added_set = new_set - old_set
    removed_set = old_set - new_set
    common_set = old_set & new_set

    changes = 0
    output = []
    for key in added_set:
        changes += 1
        output.append(DictValue(key, None, new_dict[key]))

    for key in removed_set:
        changes += 1
        output.append(DictValue(key, old_dict[key], None))

    for key in common_set:
        output.append(DictValue(key, old_dict[key], new_dict[key]))
        if str(old_dict[key]) != str(new_dict[key]):
            changes += 1

    output.sort(key=attrgetter("key"))
    return [changes, output]


def format_params_diff(parameter_diff):
    """Handles the formatting of differences in parameters.

    Args:
        parameter_diff (list): A list of DictValues detailing the
            differences between two dicts returned by
            :func:`stacker.actions.diff.diff_dictionaries`
    Returns:
        string: A formatted string that represents a parameter diff
    """

    params_output = '\n'.join([line for v in parameter_diff
                               for line in v.changes()])
    return """--- Old Parameters
+++ New Parameters
******************
%s\n""" % params_output


def diff_parameters(old_params, new_params):
    """Compares the old vs. new parameters and returns a "diff"

    If there are no changes, we return an empty list.

    Args:
        old_params(dict): old paramters
        new_params(dict): new parameters

    Returns:
        list: A list of differences
    """
    [changes, diff] = diff_dictionaries(old_params, new_params)
    if changes == 0:
        return []
    return diff


class Action(build.Action):
    """ Responsible for diff'ing CF stacks in AWS and on disk

    Generates the build plan based on stack dependencies (these dependencies
    are determined automatically based on references to output values from
    other stacks).

    The plan is then used to create a changeset for a stack using a
    generated template based on the current config.
    """

    def _diff_stack(self, stack, **kwargs):
        """Handles the diffing a stack in CloudFormation vs our config"""
        if self.cancel.wait(0):
            return INTERRUPTED

        if not build.should_submit(stack):
            return NotSubmittedStatus()

        provider = self.build_provider(stack)

        if not build.should_update(stack):
            stack.set_outputs(provider.get_outputs(stack.fqn))
            return NotUpdatedStatus()

        tags = build.build_stack_tags(stack)

        stack.resolve(self.context, provider)
        parameters = self.build_parameters(stack)

        try:
            outputs = provider.get_stack_changes(
                stack, self._template(stack.blueprint), parameters, tags
            )
            stack.set_outputs(outputs)
        except exceptions.StackDidNotChange:
            logger.info('No changes: %s', stack.fqn)
            stack.set_outputs(provider.get_outputs(stack.fqn))

        return COMPLETE

    def _generate_plan(self):
        return plan(
            description="Diff stacks",
            stack_action=self._diff_stack,
            context=self.context)

    def run(self, concurrency=0, *args, **kwargs):
        plan = self._generate_plan()
        plan.outline(logging.DEBUG)
        if plan.keys():
            logger.info("Diffing stacks: %s", ", ".join(plan.keys()))
        else:
            logger.warn('WARNING: No stacks detected (error in config?)')
        walker = build_walker(concurrency)
        plan.execute(walker)

    """Don't ever do anything for pre_run or post_run"""

    def pre_run(self, *args, **kwargs):
        pass

    def post_run(self, *args, **kwargs):
        pass
