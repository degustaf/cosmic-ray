"""Tests for the various mutation operators.
"""
import ast
import copy
import pytest

import cosmic_ray.operators.relational_operator_replacement as ROR
from cosmic_ray.counting import _CountingCore
from cosmic_ray.operators.boolean_replacer import BooleanReplacer
from cosmic_ray.operators.break_continue import (ReplaceBreakWithContinue,
                                                 ReplaceContinueWithBreak)
from cosmic_ray.operators.number_replacer import NumberReplacer
from cosmic_ray.mutating import MutatingCore


class Linearizer(ast.NodeVisitor):
    """A NodeVisitor which builds a linear list of nodes it visits.

    The basic point is to be able to take a tree of nodes and reproducably
    construct a simple list. This list is useful for e.g. comparison between
    trees.

    After using this to visit an AST, the `nodes` attribute holds the list of
    nodes.
    """
    def __init__(self):
        self.nodes = []

    def generic_visit(self, node):
        self.nodes.append(node)
        super().generic_visit(node)


def linearize_tree(node):
    "Given an AST, return a list of the nodes therein."
    l = Linearizer()
    l.visit(node)
    return l.nodes

RELATIONAL_NODE_TOKENS = {
    ast.Eq: '==',
    ast.NotEq: '!=',
    ast.Lt: '<',
    ast.LtE: '<=',
    ast.Gt: '>',
    ast.GtE: '>=',
    ast.Is: 'is',
    ast.IsNot: 'is not',
    ast.In: 'in',
    ast.NotIn: 'not in'
}

RELATIONAL_OPERATOR_SAMPLES = [
    (op, 'if x {} 1: pass'.format(RELATIONAL_NODE_TOKENS[op.from_op]))
    for op in ROR.OPERATORS
]

OPERATOR_SAMPLES = [
    (BooleanReplacer, 'True'),
    (ReplaceBreakWithContinue, 'while True: break'),
    (ReplaceContinueWithBreak, 'while False: continue'),
    (NumberReplacer, 'x = 1'),
] + RELATIONAL_OPERATOR_SAMPLES


@pytest.mark.parametrize('operator,code', OPERATOR_SAMPLES)
def test_activation_record_created(operator, code):
    node = ast.parse(code)
    core = MutatingCore(0)
    op = operator(core)
    assert core.activation_record is None
    op.visit(node)
    assert core.activation_record is not None


@pytest.mark.parametrize('operator,code', OPERATOR_SAMPLES)
def test_no_activation_record_created(operator, code):
    node = ast.parse(code)
    core = MutatingCore(1)
    op = operator(core)
    op.visit(node)
    assert core.activation_record is None


@pytest.mark.parametrize('operator,code', OPERATOR_SAMPLES)
def test_mutation_changes_ast(operator, code):
    node = ast.parse(code)
    core = MutatingCore(0)
    mutant = operator(core).visit(copy.deepcopy(node))

    orig_nodes = linearize_tree(node)
    mutant_nodes = linearize_tree(mutant)

    assert len(orig_nodes) == len(mutant_nodes)

    assert ast.dump(node) != ast.dump(mutant)


@pytest.mark.parametrize('operator,code', OPERATOR_SAMPLES)
def test_no_mutation_leaves_ast_unchanged(operator, code):
    node = ast.parse(code)

    core = MutatingCore(1)
    replacer = operator(core)
    assert ast.dump(node) == ast.dump(replacer.visit(copy.deepcopy(node)))


@pytest.mark.parametrize('operator,code', OPERATOR_SAMPLES)
def test_replacement_activated_core(operator, code):
    node = ast.parse(code)
    core = _CountingCore()
    op = operator(core)
    op.visit(node)
    assert core.count == 1



@pytest.mark.parametrize('operator,code', RELATIONAL_OPERATOR_SAMPLES)
def test_relational_operator_replacement_modifies_ast_node(operator, code):
    node = ast.parse(code)
    assert isinstance(
        node.body[0].test.ops[0],
        operator.from_op)

    core = MutatingCore(0)
    node = operator(core).visit(node)
    assert isinstance(
        node.body[0].test.ops[0],
        operator.to_op)
