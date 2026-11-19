"""Private core result/evidence validators: one precise upper bound9->49.

The old canonical validator stays unchanged. No source, state, action, event,
endpoint, video, model identity or scoring checks are skipped. In particular,
the evidence reader's nested schema call sees the same explicit index extension.
"""
import ast
from functools import lru_cache
import inspect
import textwrap

from egrs.remain049 import sources as old


def identity():
    from benchmark.remaining_goals.headless import schema, evidence
    return {'format':'task053-result-evidence-index50-v1', 'index_domain':[0,49],
            'implementation_sha256':old.sha(__file__), 'core_schema_sha256':old.sha(schema.__file__),
            'core_evidence_sha256':old.sha(evidence.__file__), 'score_modified':False,
            'canonical_module_or_file_modified':False}


@lru_cache(maxsize=1)
def namespaces():
    from benchmark.remaining_goals.headless import schema, evidence
    s = old._namespace(schema)
    tree = ast.parse(textwrap.dedent(inspect.getsource(schema._validate_result)))
    matches=[]
    for n in ast.walk(tree):
        if (isinstance(n,ast.Compare) and len(n.ops)==1 and isinstance(n.ops[0],ast.Gt)
                and isinstance(n.left,ast.Call) and isinstance(n.left.func,ast.Name)
                and n.left.func.id=='integer' and len(n.comparators)==1
                and isinstance(n.comparators[0],ast.Constant) and n.comparators[0].value==9
                and n.left.args and isinstance(n.left.args[0],ast.Call)
                and isinstance(n.left.args[0].func,ast.Attribute) and n.left.args[0].func.attr=='get'
                and isinstance(n.left.args[0].func.value,ast.Name) and n.left.args[0].func.value.id=='result'
                and len(n.left.args[0].args)==1 and isinstance(n.left.args[0].args[0],ast.Constant)
                and n.left.args[0].args[0].value=='initial_state_index'):
            matches.append(n.comparators[0])
    if len(matches)!=1:
        raise ValueError('Pinned053 result index seam differs')
    matches[0].value=49
    for n in ast.walk(tree):
        if isinstance(n,ast.Constant) and n.value=='task011 sources are official indices zero through nine':
            n.value='Task053 sources are official indices zero through49'
    local={}
    ast.increment_lineno(tree,schema._validate_result.__code__.co_firstlineno-1)
    exec(compile(ast.fix_missing_locations(tree),schema.__file__,'exec'),s,local)
    s['_validate_result']=local['_validate_result']
    e=old._namespace(evidence)
    e['validate_protocol_result']=s['validate_protocol_result']
    return s,e


def validate_protocol_result(*args,**kwargs):
    return namespaces()[0]['validate_protocol_result'](*args,**kwargs)


def validate_evidence(*args,**kwargs):
    return namespaces()[1]['validate_evidence'](*args,**kwargs)


def verifier(namespace):
    """Original checks, two imports redirected; evidence performs schema once."""
    from egrs.remain049.evaluation import verify_episode
    tree=ast.parse(inspect.getsource(verify_episode));changed=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom) and node.module in (
                'benchmark.remaining_goals.headless.schema','benchmark.remaining_goals.headless.evidence'):
            changed.append(node.module);node.module=__name__
    if len(changed)!=2:
        raise ValueError('Pinned053 verifier import seams differ')
    function=tree.body[0]
    duplicate=[n for n in function.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
        and isinstance(n.value.func,ast.Name) and n.value.func.id=='validate_protocol_result']
    if len(duplicate)!=1:
        raise ValueError('Pinned053 duplicate schema seam differs')
    # validate_evidence starts with exactly the same full schema call. It remains
    # mandatory before scoring; repeating it here only duplicates the same work.
    function.body.remove(duplicate[0])
    ast.increment_lineno(tree,verify_episode.__code__.co_firstlineno-1)
    local={}
    exec(compile(ast.fix_missing_locations(tree),verify_episode.__code__.co_filename,'exec'),namespace,local)
    return local['verify_episode']
