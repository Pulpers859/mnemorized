// Mechanical scene constraints. Clinical meaning still requires source review.
(function (root) {
  'use strict';
  const limits = Object.freeze({visualTarget:24, visualMax:34, openingTargetMin:20,
    openingTargetMax:35, openingMax:60, anchorTarget:30, anchorWarning:35});
  const wordCount = text => String(text || '').trim().split(/\s+/).filter(Boolean).length;
  // Ranged variable-length groups are unsupported; flat optionals backtrack
  // exponentially. Prefix chains in <=30-level chunks avoid both that and the
  // provider's nesting ceiling. The decoder independently checks word counts.
  function bounded(max) {
    let pattern = '^\\S+';
    for (let remaining = max - 1; remaining > 0; remaining -= 30) {
      const size = Math.min(30, remaining);
      pattern += '(\\s+\\S+'.repeat(size) + ')?'.repeat(size);
    }
    return {type:'string', pattern:pattern + '$'};
  }
  const text = () => ({type:'string', pattern:'\\S'});
  function schema(count = 8) {
    if (!Number.isInteger(count) || count < 1 || count > 10) throw new Error('Invalid scene anchor count.');
    const anchors = {};
    for (let n = 1; n <= count; n++) anchors[`anchor_${n}`] = {
      type:'object', properties:{hook:text(), narration:text(), visual:bounded(limits.visualMax),
        anchor:text(), review:text()}, required:['hook','narration','visual','anchor','review'], additionalProperties:false,
    };
    return {type:'object', properties:{scene_title:text(), opening:bounded(limits.openingMax),
      anchors:{type:'object', properties:anchors, required:Object.keys(anchors), additionalProperties:false}},
      required:['scene_title','opening','anchors'], additionalProperties:false};
  }
  function request(count = 8) {
    return {
      tools:[{name:'submit_memory_palace', strict:true,
        description:'Submit the complete source-grounded lesson. Respect all bounded fields; never clip clinical facts to fit a drawing instruction.',
        input_schema:schema(count)}],
      tool_choice:{type:'tool', name:'submit_memory_palace', disable_parallel_tool_use:true},
    };
  }
  function decode(raw, count = 8) {
    schema(count);
    const fail = reason => {throw new Error('Scene contract: ' + reason);};
    if (raw?.stop_reason !== 'tool_use' || !Array.isArray(raw.content) || raw.content.length !== 1 ||
        raw.content[0]?.type !== 'tool_use' || raw.content[0].name !== 'submit_memory_palace') {
      fail('one completed scene tool call is required; partial text is not accepted.');
    }
    const value = raw.content[0].input;
    const exact = (object, keys) => object && typeof object === 'object' && !Array.isArray(object) &&
      Object.keys(object).length === keys.length && keys.every(k => Object.hasOwn(object, k));
    const nonempty = value => typeof value === 'string' && value.trim() &&
      !/<\/?(?:scene_title|opening|vo_line|review_script)>/i.test(value) &&
      !/\n(?:HOOK|NARRATION|VISUAL|ANCHOR):/i.test(value);
    if (!exact(value, ['scene_title','opening','anchors']) || !nonempty(value.scene_title) || !nonempty(value.opening) ||
        wordCount(value.opening) > limits.openingMax) fail('invalid title or architecture opening.');
    const names = Array.from({length:count}, (_, i) => `anchor_${i + 1}`);
    if (!exact(value.anchors, names)) fail('the requested anchor inventory is incomplete or changed.');
    const reviews = [];
    const voLines = names.map((name, index) => {
      const row = value.anchors[name];
      if (!exact(row, ['hook','narration','visual','anchor','review']) ||
          Object.values(row).some(v => !nonempty(v)) || wordCount(row.visual) > limits.visualMax) {
        fail(`anchor ${index + 1} has missing, extra or oversized fields.`);
      }
      reviews.push(row.review);
      return {n:index + 1, hook:row.hook, narration:row.narration, visual:row.visual, anchor:row.anchor};
    });
    return {scene_title:value.scene_title, opening:value.opening, voLines, review_script:reviews.join('\n')};
  }
  function xml(story) {
    return `<scene_title>${story.scene_title}</scene_title>\n<opening>${story.opening}</opening>\n` +
      story.voLines.map(row => `<vo_line>\nHOOK: ${row.hook}\nNARRATION: ${row.narration}\nVISUAL: ${row.visual}\nANCHOR: ${row.anchor}\n</vo_line>`).join('\n') +
      `\n<review_script>${story.review_script}</review_script>`;
  }
  function preservesLearningText(before, after) {
    return ['scene_title','opening','review_script'].every(k => before[k] === after[k]) &&
      before.voLines.length === after.voLines.length && before.voLines.every((line, i) =>
        ['n','hook','narration','anchor'].every(k => line[k] === after.voLines[i][k]));
  }
  root.MnemorizedStoryContract = Object.freeze({limits, wordCount, schema, request, decode, xml, preservesLearningText});
})(typeof window !== 'undefined' ? window : globalThis);
