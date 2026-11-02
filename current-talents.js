'use strict';
function createCurrentTalents(data) {
  const nodes = new Map(data.talents.map(n => [n.key, n]));
  const prefix = '#mage-' + data.version + ':';
  function errors(build, level = 60, requireFull = false) {
    if (!Number.isInteger(level) || level < 1 || level > 60)
      return ['level must be an integer from 1 through 60'];
    if (!build || typeof build !== 'object' || Array.isArray(build)) return ['build must be an object'];
    const result = [];
    for (const [key, points] of Object.entries(build)) {
      if (!nodes.has(key)) result.push('unknown talent: ' + key);
      else if (!Number.isInteger(points) || points < 0 || points > nodes.get(key).max_rank)
        result.push('invalid rank: ' + key);
    }
    if (result.length) return result;
    const total = Object.values(build).reduce((a,b) => a+b, 0), budget = Math.max(0, level-9);
    if (total > budget || (requireFull && total !== budget)) result.push('point budget: ' + budget);
    for (const key of Object.keys(build).sort()) {
      if (!build[key]) continue;
      const node = nodes.get(key);
      const lower = data.talents.filter(n => n.tree === node.tree && n.required_points < node.required_points)
        .reduce((s,n) => s + (build[n.key] || 0), 0);
      if (lower < node.required_points) result.push('tier locked: ' + key);
      if (node.requires && (build[node.requires] || 0) < node.requires_rank)
        result.push('prerequisite missing: ' + key);
    }
    return result;
  }
  function encode(build) {
    const problems = errors(build); if (problems.length) throw new Error(problems.join('; '));
    return prefix + Object.keys(build).sort().filter(k => build[k]).map(k => k+'='+build[k]).join(',');
  }
  function decode(link) {
    if (typeof link !== 'string' || !link.startsWith(prefix))
      throw new Error('unsupported tree version; historical #b- links are never reinterpreted');
    const build = Object.create(null), body = link.slice(prefix.length);
    for (const item of body ? body.split(',') : []) {
      const bits = item.split('=');
      if (bits.length !== 2 || Object.hasOwn(build,bits[0]) || !/^[1-5]$/.test(bits[1]))
        throw new Error('malformed build link');
      build[bits[0]] = Number(bits[1]);
    }
    const problems = errors(build); if (problems.length) throw new Error(problems.join('; '));
    return build;
  }
  return {errors, encode, decode};
}
if (typeof module !== 'undefined' && module.exports)
  module.exports = createCurrentTalents(require('./current-talents.json'));
