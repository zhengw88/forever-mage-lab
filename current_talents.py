"""Versioned research builds. The historical #b- codec is intentionally separate."""
import json
from pathlib import Path

DATA = json.loads(Path(__file__).with_name('current-talents.json').read_text())
NODES = {n['key']: n for n in DATA['talents']}
PREFIX = '#mage-' + DATA['version'] + ':'


def errors(build, level=60, require_full=False):
    if type(level) is not int or not 1 <= level <= 60:
        return ['level must be an integer from 1 through 60']
    if not isinstance(build, dict):
        return ['build must be an object']
    result = []
    for key, points in build.items():
        if key not in NODES:
            result.append('unknown talent: ' + str(key))
        elif type(points) is not int or not 0 <= points <= NODES[key]['max_rank']:
            result.append('invalid rank: ' + key)
    if result:
        return result
    total, budget = sum(build.values()), max(0, level - 9)
    if total > budget or (require_full and total != budget):
        result.append('point budget: ' + str(budget))
    for key in sorted(build):
        if not build[key]:
            continue
        node = NODES[key]
        lower = sum(build.get(n['key'], 0) for n in NODES.values()
                    if n['tree'] == node['tree'] and n['required_points'] < node['required_points'])
        if lower < node['required_points']:
            result.append('tier locked: ' + key)
        if node['requires'] and build.get(node['requires'], 0) < node['requires_rank']:
            result.append('prerequisite missing: ' + key)
    return result


def encode(build):
    problems = errors(build)
    if problems:
        raise ValueError('; '.join(problems))
    return PREFIX + ','.join(key + '=' + str(build[key]) for key in sorted(build) if build[key])


def decode(link):
    if not isinstance(link, str) or not link.startswith(PREFIX):
        raise ValueError('unsupported tree version; historical #b- links are never reinterpreted')
    build = {}
    body = link[len(PREFIX):]
    for item in body.split(',') if body else []:
        bits = item.split('=')
        if len(bits) != 2 or bits[0] in build or bits[1] not in '12345' or len(bits[1]) != 1:
            raise ValueError('malformed build link')
        build[bits[0]] = int(bits[1])
    problems = errors(build)
    if problems:
        raise ValueError('; '.join(problems))
    return build
