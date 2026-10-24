"""Method-only, file-span adaptation over the pinned pure core resolver.

The only added root is the observed exact Mac chiliocosm prefix. Its suffix
is passed unchanged to core's supported home root, so traversal, ambiguity,
existence, containment and file hashing remain the core resolver's decisions.
No simulator/package initialization, asset writes, or path searches occur here.
"""
from copy import deepcopy
import hashlib
from html import escape
from xml.parsers import expat

RESOLVER_VERSION = 'egrs.sim.historical-xml-assets.v1'
_MAC = '/Users/yifengz/workspace/libero-dev/chiliocosm/assets/'
_HOME = '/home/yifengz/workspace/libero-dev/chiliocosm/assets/'
_MAC_RULE = 'mac_chiliocosm_exact_root_to_core_home'


def _hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest() if isinstance(text,str) else None


def _take(entries, record, value):
    """Consume by occurrence, retaining duplicate source references separately."""
    for index,entry in enumerate(entries):
        if (entry.get('tag'),entry.get('attribute'),entry.get('original')) == (record['tag'],record['attribute'],value):
            return entries.pop(index)
    return None


def resolve_source_xml(text, *, roots=None):
    # Activation/version enforcement belongs to NativeAdapter before this call.
    # Import only the pinned pure text/path module, never a simulator.
    from benchmark.remaining_goals.finish import xml_assets as core
    intermediate=text; records=[]; translated=[]
    try:
        raw,records,_=core._parse(text)
        edits=[]
        for record in records:
            value=record['original']
            change=record['allowed'] and record['span'] is not None and value.startswith(_MAC)
            translated.append(_HOME+value[len(_MAC):] if change else value)
            if change:
                edits.append((*record['span'],escape(translated[-1],quote=True).encode('utf-8')))
        for start,end,replacement in reversed(edits):
            raw=raw[:start]+replacement+raw[end:]
        intermediate=raw.decode('utf-8')
    except (ValueError,expat.ExpatError):
        # Core produces the authoritative complete parse/dependency failure.
        records=[]; translated=[]
    processed,core_report=core.resolve_xml(intermediate,roots=roots)
    report={'resolver_version':RESOLVER_VERSION,'source_xml':text,
            'source_xml_sha256':_hash(text),'intermediate_xml_sha256':_hash(intermediate),
            'processed_xml_sha256':_hash(processed),
            'intermediate_core_report':core_report,'mappings':[],'errors':[],
            'file_reference_occurrences':core_report['file_reference_occurrences'],
            'status':core_report['status'],
            'limitation':'Target hashes bind installed bytes; historical author asset byte equality remains unverified.'}
    mappings=deepcopy(core_report['mappings']); errors=deepcopy(core_report['errors'])
    for occurrence,(record,value) in enumerate(zip(records,translated)):
        # Disallowed uses of the same tag/path must consume their own error,
        # never borrow a successful direct-asset occurrence's mapping.
        entry=_take(mappings,record,value) if record['allowed'] else None
        resolved=entry is not None
        if entry is None: entry=_take(errors,record,value)
        if entry is None: continue  # Global parse/dependency errors retained below.
        core_rule=entry.get('rule')
        if record['allowed'] and 'relative_suffix' not in entry:
            try:
                namespace,suffix,core_rule=core._interpret(value)
                entry.update(root=namespace,relative_suffix='/'.join(suffix))
            except ValueError:
                pass
        entry.update(occurrence=occurrence,original=record['original'],intermediate=value)
        if value!=record['original']:
            entry.update(rule=_MAC_RULE,core_rule=core_rule)
        elif core_rule is not None:
            entry['rule']=core_rule
        report['mappings' if resolved else 'errors'].append(entry)
    report['errors'].extend(errors)
    return processed,report
